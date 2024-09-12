#!/usr/bin/env python3
from __future__ import annotations

from asyncio import sleep
from asyncio.subprocess import PIPE
from datetime import datetime
from enum import StrEnum
from functools import partial
from fractions import Fraction
from glob import glob
from pathlib import Path
from typing import Optional, Literal
import asyncio
import logging
import json
import re
import subprocess
import sys

import loguru
from aiometer import amap
from click import BadParameter, BadOptionUsage, UsageError
from ffmpeg.asyncio import FFmpeg
from humanize import naturalsize
from loguru import logger
from rich import print
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn,
    TaskProgressColumn, Task
)
from typer import Option, Abort
from typing_extensions import Annotated

from .numify import numify
from .aiotyper import AsyncTyper


# app = AsyncTyper(name='enjam', pretty_exceptions_enable=True, rich_markup_mode=None)
app = AsyncTyper(name='enjam', pretty_exceptions_enable=True)

VCodecs = StrEnum('VCodecs', 'libaom-av1 librav1e libsvtav1 libx264 libx265 copy'.split())
# 
# ffmpeg -i in.gif -c:v libaom-av1 -cpu-used 3 -threads 12 -crf 20 -arnr-max-frames 3 -arnr-strength 1 -aq-mode 1 -lag-in-frames 48 -aom-params sb-size=64:enable-qm=1:enable-dnl-denoising=0:deltaq-mode=0 -pix_fmt yuv420p10le -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -pass 1 -an -f null /dev/null && ffmpeg -i in.gif -c:v libaom-av1 -cpu-used 3 -threads 12 -crf 22 -arnr-max-frames 3 -arnr-strength 1 -aq-mode 1 -lag-in-frames 48 -aom-params sb-size=64:enable-qm=1:enable-dnl-denoising=0:deltaq-mode=0 -pix_fmt yuv420p10le -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" -pass 2 out.mp4 
# 
# ffmpeg -i in.gif -movflags faststart -pix_fmt yuv420p -c:v libaom-av1 -cpu-used 6 -threads 12 -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" out.mp4
# 
# ffmpeg -i in.gif -c:v libsvtav1 -preset 7 -crf 26 -g 200 -pix_fmt yuv420p10le -svtav1-params tune=0:film-grain=0 -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" out.mkv

#
shopen = lambda cmd: subprocess.call(cmd, shell=True)
sh_check_output = lambda cmd: subprocess.check_output(cmd, shell=True)

# Dir = Annotated[Path, Option(
#     exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True,
# )]


@app.command()
async def main(
    srcdir: Annotated[Path, Option("--src",
        exists=True, file_okay=False, dir_okay=True, readable=True, resolve_path=True,
    )] = Path('.'),
    dstdir: Annotated[str, Option("--dst",
        help=""" Output directory path. Can include variables. Example: ./{vcodec}-{crf} """,
        show_default="src"
    )] = None,
    exclude_dstdir: Annotated[bool, Option("--exclude-dstdir",
        help=""" Do not pick source files from dstdir, if it is located inside srcdir """,
    )] = True,
    jobs: int = 4,
    acodec: str = 'copy',
    vcodec: VCodecs = VCodecs.libsvtav1,
    vbitrate: Annotated[str, Option(
        help=""" If stars with x, resulting bitrate is a ratio of input file resolution.
        Example: x2.3 or 200k """,
        # callable
    )] = None,
    abitrate: str = '38k',
    crf: Annotated[int, Option(
        help="""Constant rate factor. Or qp for rav1e.""",
        show_default="24, if vbitrate is not set"
    )] = None,
    speed: str = '7',
    fprefix: Annotated[str, Option(
        help="""Output file prefix. Can include variables.
        If fprefix is not provided and dst dir includes variables, fprefix is
        set to the same pattern as dst dir name. Example: {vcodec}-{crf}-""",
        show_default="f'{dst.name}-' if '{' in dst else None"
    )] = None,
    gop: Annotated[int, Option(
        help="""Group of pictures size. The GOP size sets the maximum distance
        between key frames. Higher GOP size results in smaller file size. """
    )] = 200,
    grain: int = 0,
    write_log: bool = True,
    verbose: bool = False,
    skip_errors: Annotated[bool, Option(
        help="""Continue processing queue after one file error""",
    )] = True,
    pattern: str = '*.gif',
    # force: Annotated[
    #     bool, Option(prompt="Are you sure you want to overwrite destination files?")
    # ],
):
    """
    Batch convert videos.
    """

    # logger.configure(handlers=[])

    def stdout_filter(record: loguru.Record) -> bool:
        """ Loguru sink filter. Return True if record can be printed  to stdout. """
        if "srcfile" not in record["extra"]:
            # Outside of task's progressbar show all messages according to loglevel.
            return True

        # Inside file conversion task printing to stdout should not break
        # dynamic multiline progressbar display.
        if record['level'].no >= logging.ERROR:
            # Task log must print error only if all tasks are aborted.
            return False if skip_errors else True
        # Task log never prints INFO or lower messages.
        return False

    logger.configure(handlers=[{
        'sink': sys.stdout, 'format': '{message}', 'colorize': True,
        'filter': stdout_filter, "level": "DEBUG" if verbose else "INFO",
    }])

    if fprefix is None and dstdir and '{' in dstdir:
        # If dstdir pattern is given but not file prefix, set the file
        # prefix to be same as dstdir pattern. This is useful default
        # for convenience. Can be overriden providing --fprefix="".
        fprefix = Path(dstdir).name + '-'

    dstdir = Path(dstdir.format(**locals())) if dstdir else srcdir

    # dstdir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Destination dir {dstdir.resolve()}")

    if write_log:
        def formatter(record: loguru.Record) -> str:
            if "srcfile" in record["extra"]:
                return "{time:HH:mm:ss} {extra[srcfile]} {message}\n"
            else:
                return "{time:HH:mm:ss} {message}\n"

        logger.add(dstdir / 'enjam-log.txt', format=formatter, level='DEBUG' if verbose else 'INFO')

    logger.debug(f"sys.argv: {' '.join(sys.argv)}")
    logger.debug(str(locals()))

    if vbitrate and vbitrate.startswith('x'):
        try:
            numify(vbitrate[1:])
        except ValueError as err:
            msg = f'Wrong vbitrate format "{vbitrate}"'
            logger.error(msg)
            raise BadParameter(msg) from err

    if fprefix:
        fprefix = fprefix.format(**locals()).replace('lib', '')

    if vbitrate and crf:
        raise UsageError("Specify only one option --crf or --vbitrate")

    if not vbitrate and not crf:
        crf = 24
        logger.debug(f"Setting default crf to {crf}.")

    # source_files = glob('**/*.gif', root_dir=srcdir, recursive=True)

    # source_files = list(srcdir.rglob('*.gif'))
    source_files: list[Path] = []
    src, dst = srcdir.resolve(), dstdir.resolve()

    for file in srcdir.rglob(pattern):
        if dst.parent.is_relative_to(src) \
           and file.is_relative_to(dst) \
           and exclude_dstdir:
            # Skip files inside dstdir if it is inside srcdir.
            continue
        source_files.append(file)

    progressbar = Progress(
        SpinnerColumn(),
        # TextColumn("[progress.description]{task.fields[ratio]} {task.description}"),
        TextColumn(
            "{task.fields[info]} {task.description}" +
            (" {task.fields[frame]}/{task.fields[nframes]} frames" if verbose else "")
        ),
        # BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        # *Progress.get_default_columns(),
        # redirect_stdout=False,
        # redirect_stderr=False
    )
    
    logger.info(f'Found {len(source_files)} files')

    async def ffprobe(cmd: str) -> dict:
        """ Run ffprobe command and return JSON dict. """

        ffsubprocess = await asyncio.create_subprocess_shell(
            f'ffprobe -v quiet -print_format json {cmd}', stdout=PIPE, stderr=PIPE
        )
        stdout, stderr = await ffsubprocess.communicate()

        if ffsubprocess.returncode != 0:
            logger.debug(stderr.decode())
            logger.debug(stdout.decode())
            return 0

        return json.loads(stdout.decode())

    async def convert(srcfile: Path) -> int:
        """ Thin wrapper around main conversion job `_convert()`. Handles exceptions. """

        task = progressbar.add_task(
            # f"{srcfile}", total=1000, info=f'{num}/{len(source_files)}'
            f"[red]{srcfile}", nframes=0, frame=0,
            info=f'{len(progressbar._tasks) + 1}/{len(source_files)}',
        )
        with logger.contextualize(srcfile=srcfile):
            try:
                return await _convert(srcfile, task)
            except Exception as err:
                progressbar.update(task, completed=100, info=f'ERR ')
                logger.error(str(err))
                if not skip_errors:
                    raise err  # Abort all tasks.
        return 0

    async def _convert(srcfile: Path, task: Task) -> int:
        """ Main job. Convert one file, return compression ratio. """

        outfile = dstdir / srcfile.relative_to(srcdir).with_suffix('.mp4')

        if fprefix:
            outfile = outfile.with_stem(fprefix + outfile.stem)

        if outfile == srcfile:
            raise ValueError(
                f'Will not overwrite {srcfile.name}, choose another destinaton dir, or '
                ' set --fprefix.'
            )

        outfile.parent.mkdir(parents=True, exist_ok=True)

        nframes, resolution = None, None
        try:
            streams = await ffprobe(f'-show_streams -select_streams v "{srcfile}"')

            stream = streams["streams"][0]
            frame_rate = float(Fraction(stream["avg_frame_rate"]))

            # Mkv files store duration there instead of stream.
            duration = await ffprobe(f'-show_entries format=duration "{srcfile}"')

            duration = float(duration["format"]["duration"])

            # nframes = int(stream["nb_read_frames"])
            nframes = int(duration * frame_rate)

            resolution = int(stream["width"]) * int(stream["height"])
        except Exception as err:
            logger.warning(str(err))
            progressbar.update(task, nframes='?')
        else:
            progressbar.update(task, nframes=nframes)
        
        if vbitrate and vbitrate.startswith('x'):
            if resolution is None:
                raise Exception(
                    "Failed to get resolution to calculate requested vbitrate ratio"
                )

            vb = resolution * numify(vbitrate[1:])
        else:
            vb = vbitrate

        logger.debug(f'{srcfile} resolution {resolution} crf {crf} bitrate {vb}')

        if crf and vcodec == 'librav1e':
            quality = {'qp': crf}  # no support for crf, use quantization parameter
        else:
            quality = {'crf': crf} if crf else {'b:v': vb}

        if 'gif' in pattern:
            quality['vf'] = "scale=trunc(iw/2)*2:trunc(ih/2)*2"

        # return 0
            # .option('loglevel', 'quiet')
        # print('AAA')
        ffmpeg = FFmpeg().option("y").option('hide_banner')\
            .option('nostdin')\
            .input(srcdir/srcfile).output(outfile,
            {
                'codec:a': acodec, 'b:a': abitrate,
                # 'codec:a': acodec, 'ab': abitrate
                # 'filter:v': "setpts=4.0*PTS"
            } | {
                'copy': {"codec:v": "copy"},
                'librav1e': {"codec:v": "librav1e",
                    # 'rav1e-params': f'keyint={gop}',
                    'speed': speed,
                    # 'qp': 83
                },
                'libx265': {"codec:v": "libx265",
                    # 'rav1e-params': f'keyint={gop}',
                    # 'preset': 'veryslow',
                    'preset': speed,
                    # 'qp': 40,  # 0-51
                    # 'crf': crf,
                    'tune': 'ssim',
                },
                'libx264': {"codec:v": "libx264",
                    # 'rav1e-params': f'keyint={gop}',
                    # 'preset': 'veryslow',
                    'preset': speed,
                    # 'qp': 83
                    # 'crf': crf,
                    'tune': 'ssim',
                },
                'libsvtav1': {"codec:v": "libsvtav1",
                    # 'svtav1-params': f'tune=0:film-grain={grain}:errlog=/dev/null',
                    'svtav1-params': f'tune=0:film-grain={grain}',
                    'preset': speed,
                },
                'libaom-av1': {"codec:v": "libaom-av1",
                    'cpu-used': speed,
                    "arnr-strength": 1,
                    'tune': 'ssim',
                    # 'tune': 'psnr',
                    'aq-mode': 2,
                        # none            0
                        # variance        1
                        # complexity      2
                        # cyclic          3
                    'aom-params': ':'.join([
                        'enable-dnl-denoising=0',
                        'enable-keyframe-filtering=1',
                        # 'enable-fwd-kf=1',
                        'enable-qm=1'
                    ]),
                    'denoise-noise-level': grain,
                },
            }[vcodec] | quality,
            g=gop, pix_fmt='yuv420p10le',
            # r=0.1
        )

        @ffmpeg.on("stderr")
        def on_stderr(message: str) -> None:
            # print(123, message)
            if '[error]' not in message \
               and 'Error opening' not in message \
               and 'failed' not in message:
                return
            logger.warning(message)
            if verbose:
                progressbar.log(f'{srcfile} {message}')

        @ffmpeg.on("progress")
        def on_progress(progress):
            # print(f"{progress.frame}/{nframes}")
            progressbar.update(
                task, frame=progress.frame,
                completed=(int(progress.frame) / nframes * 100) if nframes else 0
            )

        await ffmpeg.execute()

        # await sleep(0.5)
        ratio = float(srcfile.stat().st_size) / outfile.stat().st_size

        progressbar.update(task, completed=100, info=f'{ratio: >3.1f}x')
        logger.debug(f"Written {naturalsize(outfile.stat().st_size, gnu=True)}, "
                     f"comression ratio {ratio:.1f}; "
                     f"took {progressbar._tasks[task].elapsed:.3f}s {outfile}")

        return ratio
                
    start_time = datetime.now()
    ratios = []

    with progressbar:
        async with amap(convert, source_files, max_at_once=jobs) as results:
            async for ratio in results:
                ratios.append(ratio)

    await sleep(0.001)

    positive = [x for x in ratios if x > 0]
    if positive:
        logger.info(f'Average compression ratio: {sum(positive) / len(positive):.1f}')

    logger.info(f'All finished in {datetime.now() - start_time}')

    logger.info(f'Successfully processed {len(positive)} files')

    if len(ratios) - len(positive) > 0:
        logger.info(f'Failed to process {len(ratios) - len(positive)} files')

    
if __name__ == '__main__':
    app()
