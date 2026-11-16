"""Background worker: the crawler pipeline.

crawl_jobs (timer, once a day at 13:00 UTC)
    -> raw snapshot JSON to Blob Storage (container: raw-crawls)
    -> one message per job to Queue Storage (queue: jobs-to-process)
process_job (queue trigger)
    -> dedupe hash -> upsert into Azure SQL -> score against saved filters
    -> (next) push live alert
"""
import json
import logging

import azure.functions as func

from crawler.run import crawl
from processor import db, pipeline

app = func.FunctionApp()


@app.timer_trigger(arg_name="timer", schedule="0 0 13 * * *", run_on_startup=False)
@app.blob_output(arg_name="snapshot",
                 path="raw-crawls/{DateTime}.json",
                 connection="AzureWebJobsStorage")
@app.queue_output(arg_name="outbox",
                  queue_name="jobs-to-process",
                  connection="AzureWebJobsStorage")
def crawl_jobs(timer: func.TimerRequest,
               snapshot: func.Out[str],
               outbox: func.Out[list[str]]) -> None:
    raw, jobs = crawl()
    snapshot.set(json.dumps(raw))
    outbox.set([json.dumps(job) for job in jobs])
    logging.info("Crawl finished: %d jobs queued, %d source errors",
                 len(jobs), len(raw["errors"]))


@app.queue_trigger(arg_name="msg",
                   queue_name="jobs-to-process",
                   connection="AzureWebJobsStorage")
def process_job(msg: func.QueueMessage) -> None:
    job = json.loads(msg.get_body().decode("utf-8"))
    repo = db.connect()
    try:
        result = pipeline.process_job(repo, job, pipeline.load_filters(repo))
        repo.commit()
    except Exception:
        repo.rollback()
        raise  # the message is retried, then moved to the poison queue
    finally:
        repo.close()
    logging.info("%s job %d: %s | %s | %s (best score %s)",
                 result.status, result.job_id, job["company"], job["title"],
                 job["location"], result.best_score)
    # TODO: send a SignalR message when a new job beats a filter's min_score
