# startbackup.py
# Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import logging
import tarfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

log = logging.getLogger('ts2.backup')


class Command(BaseCommand):
    help = 'Periodically archive the instance folder to another location.'

    requires_migrations_checks = []
    requires_system_checks = []

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '-o', '--target', action='store', dest='target', required=True,
            help='Destination folder, will be created if it does not exist.',
        )
        parser.add_argument(
            '-p', '--prefix', action='store', dest='prefix',
            help='Prefix for archive filenames.', default='backup',
        )
        parser.add_argument(
            '-t', '--interval', action='store', dest='interval',
            help='Interval for backups in seconds. Default is 3600',
            type=int, default=3600,
        )

    def handle(self, *args, target: str, prefix: str, interval: int, **options):
        dst = Path(target)
        if not dst.exists():
            dst.mkdir()
        if not dst.is_dir():
            raise ValueError(f'{dst} is not a folder.')
        try:
            asyncio.run(self.run(dst, interval, prefix))
        except KeyboardInterrupt:
            return

    def archive(self, src: Path, dst: Path, prefix='backup') -> bool:
        now = datetime.now(tz=timezone.utc)
        fmttime = now.strftime('%Y%m%d.%H%M%S%z')
        filename = f'{prefix}.{src.name}.{fmttime}.tar.gz'
        target = dst / filename
        try:
            tar = tarfile.open(target, 'x:gz')
        except OSError as e:
            log.error(f'Failed to open tarfile at {target}: {e}')
            return False
        try:
            tar.add(src, src.name)
        except OSError as e:
            log.error(f'Failed to add {src} to tarfile: {e}')
            return False
        else:
            tar.close()
            log.info(f'Created backup {filename}')
            return True

    def clean(self, src: Path, dst: Path, prefix: str, schedules: list[float]):
        filename = f'{prefix}.{src.name}'
        archives = [p for p in dst.iterdir() if (
            p.name.startswith(filename)
            and ''.join(p.suffixes[-2:]) == '.tar.gz'
        )]
        archives = sorted(archives, key=lambda p: p.stat().st_mtime, reverse=True)
        now = datetime.now(tz=timezone.utc).timestamp()
        delete: defaultdict[list[Path]] = defaultdict(list)
        schedules = [*schedules]
        for tar in archives:
            if not schedules:
                break
            duration = schedules[-1]
            atime = tar.stat().st_atime
            if now - 2 * duration < atime < now - duration:
                delete[duration].append(tar)
            elif now - 2 * duration > atime:
                schedules.pop()
        for files in delete.values():
            for tar in files[:-1]:
                try:
                    tar.unlink()
                except OSError:
                    pass

    async def run(self, dst: Path, interval: int, prefix: str = 'backup'):
        src: Path = settings.INSTANCE_DIR
        while True:
            self.archive(src, dst, prefix)
            self.clean(src, dst, prefix, (86400,))
            await asyncio.sleep(interval)
