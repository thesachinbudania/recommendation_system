from typing import Any
import json
from celery import shared_task, chain, group
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.exceptions import ValidationError
import logging
from movies.services import parse_csv, parse_json

logger = logging.getLogger(__name__)

def split_csv_file(file_path: str, chunk_size_mb: int = 100) -> list[str]:
    chunk_paths = []
    part = 1
    current_chunk_size = 0
    chunk_lines = []

    with default_storage.open(file_path, "r") as file:
        for line in file:
            line_size = len(line.encode("utf-8"))
            if (current_chunk_size + line_size) > (chunk_size_mb * 1024 * 1024):
                chunk_file_name = f"{file_path}_part_{part}.csv"
                default_storage.save(chunk_file_name, ContentFile("".join(chunk_lines)))
                chunk_paths.append(chunk_file_name)
                chunk_lines = []
                chunk_lines = [line]
                current_chunk_size = line_size
                part += 1
            else:
                chunk_lines.append(line)
                current_chunk_size += line_size

    if chunk_lines: # Save the last chunk if there is any
        chunk_file_name = f"{file_path}_part_{part}.csv"
        default_storage.save(chunk_file_name, ContentFile("".join(chunk_lines)))
        chunk_paths.append(chunk_file_name)

    return chunk_paths


def split_json_file(file_path: str, chunk_size_mb: int = 100) -> list[str]:
    chunk_paths = []
    part = 1
    current_chunk_size = 0
    chunk_objects = []

    with default_storage.open(file_path, "r") as file:
        objects = json.load(file)

        for obj in objects:
            obj_str = json.dumps(obj)
            obj_size = len(obj_str.encode("utf-8"))
            if current_chunk_size + obj_size > chunk_size_mb * 1024 * 1024:
                chunk_file_name = f"{file_path}_part_{part}.json"
                default_storage.save(chunk_file_name, ContentFile(json.dumps(chunk_objects)))
                chunk_paths.append(chunk_file_name)
                chunk_objects = [obj]
                current_chunk_size = obj_size
                part += 1
            else:
                chunk_objects.append(obj)
                current_chunk_size = obj_size
    if chunk_objects:
        chunk_file_name = f"{file_path}_part_{part}.json"
        default_storage.save(chunk_file_name, ContentFile(json.dumps(chunk_objects)))
        chunk_paths.append(chunk_file_name)
    return chunk_paths

@shared_task
def split_file_task(file_name: str, file_type: str) -> list[str]:
    if file_type == "text/csv":
        result = split_csv_file(file_name)
    elif file_type == "application/json":
        result = split_json_file(file_name)
    else:
        raise ValidationError("Invalid file type")
    default_storage.delete(file_name)
    return result


@shared_task
def process_chunks(chunk_paths: list, file_type: str) -> int:
    # Create a group of tasks to process each chunk
    task_group = group(process_chunk.s(chunk_path, file_type) for chunk_path in chunk_paths)
    return task_group.apply_async()

@shared_task
def process_chunk(chunk_path: str, file_type: str) -> int:
    logger.info('This is the chunk path %s and file_type %s', chunk_path, file_type)
    with default_storage.open(chunk_path, "r") as file:
        if file_type == "text/csv":
            result = parse_csv(file)
        elif file_type == "application/json":
            result = parse_json(file)
        else:
            raise ValidationError("Invalid file type")
        default_storage.delete(chunk_path)
    logger.info("Processed movies %s", result)
    return result

@shared_task
def process_file(file_name: str, file_type: str) -> Any:
    if not default_storage.exists(file_name):
        raise ValidationError(f"File does not exist in storage.")

    # Create chain of chunking and processing tasks
    workflow = chain(
        split_file_task.s(file_name, file_type),
        process_chunks.s(file_type),
    )
    result = workflow.apply_async()
    return result