import os
import time
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

class Command(BaseCommand):
    help = 'Backup the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            default=None,
            help='Directory where backup will be stored',
        )
        parser.add_argument(
            '--keep',
            type=int,
            default=0,
            help='Keep only the N most recent backups in the output dir (0 = keep all)',
        )

    def handle(self, *args, **options):
        # Get the database settings
        db_settings = settings.DATABASES['default']
        db_engine = db_settings['ENGINE']
        
        # Create backup directory if it doesn't exist
        output_dir = options['output_dir']
        if output_dir is None:
            output_dir = Path(settings.BASE_DIR) / 'backups'
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for the backup file
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        
        if 'sqlite3' in db_engine:
            # SQLite backup
            db_path = db_settings['NAME']
            backup_file = os.path.join(output_dir, f'db_backup_{timestamp}.sqlite3')
            
            try:
                self.stdout.write(self.style.SUCCESS(f'Backing up SQLite database to {backup_file}...'))

                # sqlite3 backup API = consistent snapshot even while server writes
                # (plain file copy can capture a mid-transaction, corrupt state).
                import sqlite3
                from contextlib import closing
                with closing(sqlite3.connect(str(db_path))) as src, \
                     closing(sqlite3.connect(backup_file)) as dst:
                    src.backup(dst)

                self.stdout.write(self.style.SUCCESS('Database backup completed successfully!'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error backing up database: {e}'))
        
        elif 'mysql' in db_engine:
            # MySQL backup
            db_name = db_settings['NAME']
            db_user = db_settings['USER']
            db_password = db_settings['PASSWORD']
            db_host = db_settings['HOST']
            db_port = db_settings['PORT']
            
            backup_file = os.path.join(output_dir, f'db_backup_{timestamp}.sql')
            
            try:
                # Use mysqldump command
                self.stdout.write(self.style.SUCCESS(f'Backing up MySQL database to {backup_file}...'))
                
                # Build the mysqldump command
                cmd = [
                    'mysqldump',
                    f'--user={db_user}',
                    f'--host={db_host}',
                    f'--port={db_port}',
                    '--single-transaction',
                    '--routines',
                    '--triggers',
                    '--databases', db_name
                ]
                
                # Add password if provided
                if db_password:
                    cmd.append(f'--password={db_password}')
                
                # Execute the command and save output to file
                with open(backup_file, 'w') as f:
                    subprocess.run(cmd, stdout=f, check=True)
                
                self.stdout.write(self.style.SUCCESS('Database backup completed successfully!'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error backing up database: {e}'))
        
        else:
            self.stdout.write(self.style.ERROR(f'Unsupported database engine: {db_engine}'))
            return

        keep = options['keep']
        if keep > 0:
            backups = sorted(
                Path(output_dir).glob('db_backup_*'),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old in backups[keep:]:
                old.unlink()
                self.stdout.write(f'Pruned old backup: {old.name}')
