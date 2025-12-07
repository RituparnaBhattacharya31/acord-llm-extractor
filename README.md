# ACORD LLM Extractor

![Python](https://img.shields.io/badge/python-3.12-blue)
![AWS Lambda](https://img.shields.io/badge/aws-lambda-orange)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Serverless](https://img.shields.io/badge/serverless-event--driven-lightgrey)

Event-driven ACORD 140 PDF extraction pipeline using AWS Lambda, Google Gemini, S3, and DynamoDB. Automatically converts ACORD forms into clean, structured JSON using serverless architecture and LLM intelligence.

Full Description
A fully serverless and automated pipeline for extracting structured JSON data from ACORD 140 insurance PDF forms using:
➡️AWS Lambda (Python)
➡️Google Gemini (LLM)
➡️Amazon S3 event triggers
➡️Lambda Layers (for 70MB Gemini dependencies)
➡️DynamoDB storage

This project demonstrates how to combine LLMs with AWS serverless architecture to process incoming PDF documents with zero manual effort. When a new ACORD form is uploaded to an S3 bucket, the system automatically:

➡️Downloads and processes the PDF
➡️Extracts structured fields using Gemini
➡️Validates the extracted data
➡️Stores the parsed JSON in S3
➡️Saves the full extraction record in DynamoDB

Ideal as a POC or foundation for a production-ready, event-driven document-processing system.
