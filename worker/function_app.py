"""Background worker: the crawler pipeline.

crawl_jobs (timer, every 2 hours)
    -> raw snapshot JSON to Blob Storage (container: raw-crawls)
    -> one message per job to Queue Storage (queue: jobs-to-process)
"""
import json
import logging

import azure.functions as func

from crawler.run import crawl

app = func.FunctionApp()


@app.timer_trigger(arg_name="timer", schedule="0 0 */2 * * *", run_on_startup=False)
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

