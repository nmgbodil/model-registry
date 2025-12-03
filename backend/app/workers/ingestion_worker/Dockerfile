# backend/app/workers/ingestion_worker/Dockerfile

# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.11

RUN yum install -y gcc gcc-c++ make git && yum clean all

# Lambda code lives under /var/task
WORKDIR /var/task
COPY backend/ ./backend

# Make ingestion_worket a top-level import root and keep HF caches in /tmp
ENV PYTHONPATH=/var/task/backend/app/workers/ingestion_worker \
    HF_HOME=/tmp/hf \
    HF_HUB_CACHE=/tmp/hf/hub \
    HF_DATASETS_CACHE=/tmp/hf/datasets \
    HF_METRICS_CACHE=/tmp/hf/metrics \
    TRANSFORMERS_CACHE=/tmp/hf/transformers

WORKDIR /var/task/backend
RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir -e .

# Tell Lambda which handler to call
#    module.path.to.function
CMD ["app.workers.ingestion_worker.handler.lambda_handler"]
