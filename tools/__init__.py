from .weather import get_current_weather, get_weather_forecast
from .search import search_web, fetch_webpage_content
from .files import list_directory, read_file, write_file, delete_file, delete_directory
from .terminal import run_python_script
from .knowledge import build_knowledge_base, search_knowledge_base

# Export all active tools to main.py
ALL_TOOLS = [
    get_current_weather,
    get_weather_forecast,
    search_web,
    fetch_webpage_content,
    list_directory,
    read_file,
    write_file,
    delete_file,
    delete_directory,
    run_python_script,
    build_knowledge_base,
    search_knowledge_base
]