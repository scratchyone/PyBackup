__version__ = '0.1.0'
import click
from google.cloud import storage
from datetime import datetime
from os import path
from discord_webhook import DiscordWebhook, DiscordEmbed
import subprocess


@click.command()
@click.option('--file', help='Path to the file to backup', required=True)
@click.option('--webhook',
              default=None,
              help='The URL of the discord webhook to send status messages to.'
              )
@click.option('--rename',
              default=None,
              help='The uploaded file name (supports strftime formatting)')
@click.option('--bucket',
              help='The name of the GCP Bucket to upload to',
              required=True)
@click.option('--error_ping',
              default=None,
              help='The ID of the discord user to ping when an error occurs')
@click.option('--job_name',
              default=None,
              help='The name of the backup job for logging')
@click.option(
    '--log_success/--no_success_log',
    default=True,
    help=
    'Choose if the bot should send webhook messages when the backup succeeds')
@click.option('--prebackup',
              default=None,
              help='Command to run before backing up')
def backup(file, webhook, rename, bucket, error_ping, job_name, log_success,
           prebackup):
    """Simple backup tool"""
    try:
        if rename == None:
            f1, e = path.splitext(path.basename(file))
            name = f1 + "-%Y-%m-%dT%H:%M:%S" + e
        else:
            name = rename
        d = datetime.now()
        name = d.strftime(name)

        if prebackup != None:
            subprocess.run([prebackup],
                           shell=True,
                           check=True,
                           capture_output=True,
                           text=True)

        storage_client = storage.Client()
        gcpbucket = storage_client.bucket(bucket)
        blob = gcpbucket.blob(name)
        blob.upload_from_filename(file)
        print(blob.self_link)

        print(
            "File {} uploaded to https://console.cloud.google.com/storage/browser/_details/{}/{}"
            .format(file, bucket, name))
        if webhook != None and log_success:
            webhook = DiscordWebhook(url=webhook)
            embed = DiscordEmbed(
                title=(job_name if job_name != None else file) +
                " Backed Up Successfully",
                url=
                "https://console.cloud.google.com/storage/browser/_details/{}/{}"
                .format(bucket, name),
                description=
                'This backup job has completed successfully and the file has been uploaded to GCP.',
                color=0x3dfc5b)
            webhook.add_embed(embed)
            response = webhook.execute()

    except Exception as e:
        if (webhook != None):
            webhook = DiscordWebhook(url=webhook,
                                     content="<@" + error_ping +
                                     ">" if error_ping != None else "")
            em = str(e)
            if isinstance(e, subprocess.CalledProcessError):
                em = e.stderr if e.stderr else "Failed to capture stderr of prebackup command"
            embed = DiscordEmbed(
                title='Error',
                description='An error has occured while attempting to backup '
                + (job_name if job_name != None else "`" + file + "`") +
                "\n```\n" + em + "```",
                color=0xff5858)
            webhook.add_embed(embed)
            response = webhook.execute()
        raise e


if __name__ == '__main__':
    backup()
