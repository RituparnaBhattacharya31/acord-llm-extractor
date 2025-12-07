FROM public.ecr.aws/lambda/python:3.12

# Install system deps for pdf2image/poppler if needed
RUN yum -y install poppler-utils && yum -y install which

# Copy requirements and install
COPY requirements.txt  .
RUN python3.12 -m pip install --upgrade pip
RUN python3.12 -m pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Copy function code
COPY . ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (file.function)
CMD [ "handler.lambda_handler" ]
