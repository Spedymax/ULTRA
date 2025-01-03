
import openai
from apikey import weather_api_key, DEFAULT_LOCATION, UNIT, spotify_client_id, spotify_client_secret
from datetime import datetime
import sympy as smpy
from urllib3.exceptions import NotOpenSSLWarning
import keyboard
import sys
from app_paths import APP_PATHS
from app_subsets import AppSubsetManager
sys.stdout.reconfigure(encoding='utf-8')
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import json
print('Loading...')

app_subset_manager = AppSubsetManager()


def expand_path(path):
    """Expand environment variables and user paths in the given path."""
    expanded = os.path.expandvars(os.path.expanduser(path))
    return expanded


def find_executable_path(app_name):
    """
    Find the executable path for a given application name.
    Returns the path if found, None otherwise.
    """
    system = platform.system().lower()
    if system not in APP_PATHS:
        return None

    # Convert app_name to lowercase for case-insensitive comparison
    app_name_lower = app_name.lower()

    # Search through all apps in the system's dictionary
    for app_info in APP_PATHS[system].values():
        # Check if the app_name matches any of the common names
        if app_name_lower in app_info['common_name']:
            # Try each possible path
            for path in app_info['paths']:
                expanded_path = expand_path(path)
                if os.path.exists(expanded_path):
                    return expanded_path

    return None


def control_pc(action, delay=0):
    """
    Control PC operations like restart, shutdown, sleep, or lock.
    """
    print(f"[Ultra is preparing to {action} the PC...]")

    if delay > 0:
        time.sleep(delay)

    system = platform.system().lower()

    try:
        if system == 'windows':
            commands = {
                "restart": ["shutdown", "/r", "/t", "0"],
                "shutdown": ["shutdown", "/s", "/t", "0"],
                "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                "lock": ["rundll32.exe", "user32.dll,LockWorkStation"]
            }
        elif system == 'darwin':  # macOS
            commands = {
                "restart": ["sudo", "shutdown", "-r", "now"],
                "shutdown": ["sudo", "shutdown", "-h", "now"],
                "sleep": ["pmset", "sleepnow"],
                "lock": ["login", "-f", "root",
                         "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"]
            }
        elif system == 'linux':
            commands = {
                "restart": ["sudo", "shutdown", "-r", "now"],
                "shutdown": ["sudo", "shutdown", "-h", "now"],
                "sleep": ["systemctl", "suspend"],
                "lock": ["loginctl", "lock-session"]
            }

        if action in commands:
            subprocess.run(commands[action], check=True)
            return json.dumps({
                "PC Control Success": f"Successfully initiated {action} command"
            })
        else:
            return json.dumps({
                "PC Control Error": f"Unknown action: {action}"
            })

    except subprocess.CalledProcessError as e:
        return json.dumps({
            "PC Control Error": f"Error during {action}: {str(e)}"
        })
    except Exception as e:
        return json.dumps({
            "PC Control Error": f"Unexpected error during {action}: {str(e)}"
        })


def open_application(app_name: str, arguments: str = "") -> str:
    """
    Open a Windows application using PowerShell Start-FromWinStartMenuApp function.

    Args:
        app_name: Name of the application to open
        arguments: Command line arguments (optional)

    Returns:
        JSON string with result status and message
    """
    try:
        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        ps_script_path = os.path.join(script_dir, "Start-FromWinStartMenuApp.ps1")

        # Prepare PowerShell command
        ps_command = [
            'powershell',
            '-ExecutionPolicy', 'Bypass',
            '-File', ps_script_path,
            app_name
        ]

        # Add arguments if provided
        if arguments:
            ps_command.extend(['-Arguments', arguments])

        # Execute PowerShell script
        result = subprocess.run(
            ps_command,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # Parse PowerShell output (assuming it's in hashtable format)
        output = result.stdout.strip()

        if result.returncode == 0 and "Success" in output:
            return json.dumps({
                "status": "success",
                "message": output,
                "no_speak": True
            })
        else:
            raise Exception(output or result.stderr)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error opening {app_name}: {str(e)}",
            "no_speak": True
        })

def manage_app_subset(action: str, subset_name: str, modification_type: str = None, apps: list[str] = None) -> str:
    """
    Manage application subsets (create, modify, delete, list, or open them).
    """
    print(f"[Ultra is managing app subset '{subset_name}' with action: {action}...]")

    try:
        if action == "create" and apps:
            result = app_subset_manager.create_subset(subset_name, apps)
            return json.dumps(result)

        elif action == "delete":
            result = app_subset_manager.delete_subset(subset_name)
            return json.dumps(result)

        elif action == "modify" and modification_type and apps:
            result = app_subset_manager.modify_subset(subset_name, modification_type, apps)
            return json.dumps(result)

        elif action == "list":
            subsets = app_subset_manager.list_subsets()
            return json.dumps({
                "status": "success",
                "subsets": subsets
            })

        elif action == "open":
            apps_to_open = app_subset_manager.get_subset_apps(subset_name)
            if not apps_to_open:
                return json.dumps({
                    "status": "error",
                    "message": f"No applications found in subset '{subset_name}'",
                    "no_speak": True
                })

            # Open each application in the subset
            results = []
            for app in apps_to_open:
                try:
                    app_result = json.loads(open_application(app))
                    results.append(app_result.get("Application Success", f"Opened {app}"))
                except Exception as e:
                    results.append(f"Failed to open {app}: {str(e)}")

            return json.dumps({
                "status": "success",
                "message": f"Opening applications in subset '{subset_name}'",
                "results": results,
                "no_speak": True  # Add flag to prevent speaking
            })

        return json.dumps({
            "status": "error",
            "message": "Invalid action or missing required parameters"
        })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Error managing app subset: {str(e)}"
        })


def open_browser(url, browser="default"):
    """
    Open a URL in the default web browser or a specific browser.
    """
    print(f"[Ultra is opening {url} in the browser...]")

    try:
        if browser == "default":
            webbrowser.open(url)
        else:
            # Find the browser executable path
            browser_path = find_executable_path(browser)

            if browser_path:
                subprocess.Popen([browser_path, url])
            else:
                # Fallback to default browser if specified browser not found
                webbrowser.open(url)

        return json.dumps({
            "Browser Success": f"Successfully opened {url} in {browser} browser"
        })
    except Exception as e:
        return json.dumps({
            "Browser Error": f"Error opening URL {url}: {str(e)}"
        })




was_spotify_playing = False
original_volume = None
user_requested_pause = False

def get_current_weather(location=None, unit=UNIT):
    print(" ")
    """Get the current weather in a given location and detailed forecast"""
    if location is None:
        location = DEFAULT_LOCATION
    API_KEY = weather_api_key
    base_url = "http://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": API_KEY,
        "q": location,
        "days": 1
    }
    
    response = requests.get(base_url, params=params)
    data = response.json()

    if response.status_code == 200 and 'current' in data and 'forecast' in data and data['forecast']['forecastday']:
        weather_info = {
        "location": location,
        "temperature": data["current"]["temp_f"],
        "feels_like": data["current"]["feelslike_f"],
        "max_temp": data['forecast']['forecastday'][0]['day']['maxtemp_f'],
        "min_temp": data['forecast']['forecastday'][0]['day']['mintemp_f'],
        "unit": "fahrenheit",
        "forecast": data["current"]["condition"]["text"],
        "wind_speed": data["current"]["wind_mph"],
        "wind_direction": data["current"]["wind_dir"],
        "humidity": data["current"]["humidity"],
        "pressure": data["current"]["pressure_in"],
        "rain_inches": data["current"]["precip_in"],
        "sunrise": data['forecast']['forecastday'][0]['astro']['sunrise'],
        "sunset": data['forecast']['forecastday'][0]['astro']['sunset'],
        "moonrise": data['forecast']['forecastday'][0]['astro']['moonrise'],
        "moonset": data['forecast']['forecastday'][0]['astro']['moonset'],
        "moon_phase": data['forecast']['forecastday'][0]['astro']['moon_phase'],
        "will_it_rain": data['forecast']['forecastday'][0]['day']['daily_will_it_rain'],
        "chance_of_rain": data['forecast']['forecastday'][0]['day']['daily_chance_of_rain'],
        "uv": data["current"]["uv"]
        }
    else:
        weather_info = {
            "error": "Unable to retrieve the current weather. Try again in a few seconds. If this happens multiple times, close Ultra and reopen him."
        }
    print(f"[Ultra is finding the current weather in {location}...]")
    return json.dumps(weather_info)
    
def perform_math(input_string):
    print("[Ultra is calculating math...]")
    print(" ")

    tasks = input_string.split(', ')
    responses = []

    for task in tasks:
        try:
            # Check if the task is an equation (contains '=')
            if '=' in task:
                # Split the equation into lhs and rhs
                lhs, rhs = task.split('=')
                lhs_expr = smpy.sympify(lhs)
                rhs_expr = smpy.sympify(rhs)

                # Identify all symbols (variables) in the equation
                symbols = lhs_expr.free_symbols.union(rhs_expr.free_symbols)

                # Solve the equation
                # For multiple symbols, solve() returns a list of solution dictionaries
                result = smpy.solve(lhs_expr - rhs_expr, *symbols)
            else:
                # If not an equation, directly evaluate the expression
                expression = smpy.sympify(task)
                result = expression.evalf()

            responses.append(f"Result of '{task}' is {result}.")

        except Exception as e:
            responses.append(f"Error in '{task}': {str(e)}")
    note = "Format the following in LaTeX code format:"
    final_response = note + " ".join(responses)
    return json.dumps({"Math Result": final_response})

memory_file_path = None

def get_memory_file_path():
    """Return the full path to the memory.txt file. Create the file if it doesn't exist."""
    global memory_file_path

    if memory_file_path:
        return memory_file_path

    current_dir = os.path.dirname(os.path.abspath(__file__))
    memory_file_path = os.path.join(current_dir, "memory.txt")

    if not os.path.exists(memory_file_path):
        with open(memory_file_path, 'w') as file:
            json.dump([], file)

    return memory_file_path

def memorize(operation, data=None):
    """Store, retrieve, or clear data in your memory."""
    file_path = get_memory_file_path()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with open(file_path, 'r') as file:
            memory = json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        memory = []

    if operation == "store" and data is not None:
        print("[Ultra is storing memory data...]")
        memory.append({
            "data": data,
            "store_time": current_time,
            "retrieve_time": None
        })

    elif operation == "retrieve":
        print("[Ultra is retrieving memory data...]")
        if not memory:
            return json.dumps({"Memory Message for No Data": "No data stored yet"})

        for item in memory:
            item["retrieve_time"] = current_time

        retrieved_data = [{"data": item["data"], "store_time": item["store_time"], "retrieve_time": current_time} for item in memory]
        return json.dumps({"Memory Message for Retrieved Data": f"Data retrieved on {current_time}", "data": retrieved_data})

    elif operation == "clear":
        print("[Ultra is clearing memory data...]")
        memory = []

    with open(file_path, 'w') as file:
        json.dump(memory, file)

    if operation == "store":
        return json.dumps({"Memory Message for Success": f"Data stored successfully on {current_time}"})
    elif operation == "clear":
        return json.dumps({"Memory Message for Erase": "Memory cleared successfully"})

def get_current_datetime(mode="date & time"):
    """Get the current date and/or time"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%I:%M:%S %p")
    
    if mode == "date":
        print("[Ultra is finding the Date...]")
        response = {"datetime": date_str}
        datetime_response = "This is today's date, use this to answer the users question, if it is not relevant, do not say it: " + response["datetime"]
    elif mode == "time":
        print("[Ultra is finding the Time...]")
        response = {"datetime": time_str}
        datetime_response = "This is the current time, use this to answer the users question, if it is not relevant, do not say it: " + response["datetime"]
    else:
        print("[Ultra is finding the Date and Time...]")
        response = {"datetime": f"{date_str} {time_str}"}
        datetime_response = "This is today's date and time, use this to answer the users question, if it is not relevant, do not say it: " + response["datetime"]
    
    # Return the datetime response as a JSON string
    return json.dumps({"Datetime Response": datetime_response})

import spotipy
from spotipy.oauth2 import SpotifyOAuth

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotify_client_id,
                                               client_secret=spotify_client_secret,
                                               redirect_uri="http://localhost:8080/callback",
                                               scope = "user-library-read user-modify-playback-state user-read-playback-state user-read-currently-playing user-read-playback-position user-read-private user-read-email"))

def search_and_play_song(song_name: str):
    print(f"[Ultra is searching for '{song_name}' on Spotify...]")
    results = sp.search(q=song_name, limit=1)
    if results and results['tracks'] and results['tracks']['items']:
        song_uri = results['tracks']['items'][0]['uri']
        song_name = results['tracks']['items'][0]['name']
        try:
            sp.start_playback(uris=[song_uri])
            response = json.dumps({
                "Spotify Success Message": f"Tell the user 'The song \"{song_name}\" is now playing.' If you have anything else to say, be very concise."
            }, indent=4)
        except spotipy.exceptions.SpotifyException as e:
            response = json.dumps({
        "Spotify Update Session Message": "Inform the user to open Spotify before playing a song. They may need to play and pause a song for recognition of an open Spotify session. If they recently purchased Spotify Premium, it can take up to 15 minutes to register due to slow server response.",
        "Error Detail": str(e)
    }, indent=4)
    else:
        response = json.dumps({
            "Spotify Fail Message": "Sorry, I couldn't find the song you requested."
        }, indent=4)

    return response
    
current_model = "gpt-4o-mini"

def toggle_spotify_playback(action):
    global was_spotify_playing, user_requested_pause
    print(f"[Ultra is updating Spotify playback...]")
    try:
        current_playback = sp.current_playback()

        if action == "pause":
            user_requested_pause = True
            if current_playback and current_playback['is_playing']:
                sp.pause_playback()
                was_spotify_playing = True
                set_spotify_volume(original_volume)
                return json.dumps({"Success Message": "Say: Okay, it's paused."})
            else:
                set_spotify_volume(original_volume)
                was_spotify_playing = False
                return json.dumps({"Success Message": "Say: Okay, it's paused."})

        elif action == "unpause":
            user_requested_pause = False
            if current_playback and not current_playback['is_playing']:
                sp.start_playback()
                return json.dumps({"Success Message": "Say: Okay, it's unpaused."})
            else:
                return json.dumps({"Success Message": "Say: Okay, it's unpaused."})

        elif action == "toggle":
            if current_playback and current_playback['is_playing']:
                sp.pause_playback()
                was_spotify_playing = False
                return json.dumps({"Success Message": "Say: Okay, I paused the song."})
            else:
                sp.start_playback()
                was_spotify_playing = True
                return json.dumps({"Success Message": "Say: Okay, I unpaused the song."})

        else:
            return json.dumps({"Invalid Action Message": "Invalid action specified"})

    except Exception as e:
        return json.dumps({"Error Message": str(e)})


def set_spotify_volume(volume_percent):
    global was_spotify_playing, original_volume, user_requested_pause
    original_volume = volume_percent
    print(f"[Ultra is changing Spotify volume to {volume_percent}%...]")
    try:
        sp.volume(volume_percent)
        return json.dumps({"Spotify Volume Success Message": f"Spotify volume set to {volume_percent}%"})
    except Exception as e:
        return json.dumps({"Spotify Volume Error Message": str(e)})

def set_spotify_volume2(volume_percent):
    print(f"[Ultra is changing Spotify volume to {volume_percent}%...]")
    try:
        sp.volume(volume_percent)
        return json.dumps({"Spotify Volume Success Message": f"Spotify volume set to {volume_percent}%"})
    except Exception as e:
        return json.dumps({"Spotify Volume Error Message": str(e)})

import ctypes
from ctypes import cast, POINTER, wintypes
import json
import math

# Windows API constants
WINMM = ctypes.WinDLL('winmm')
WINMM.waveOutGetVolume.argtypes = [wintypes.HANDLE, POINTER(wintypes.DWORD)]
WINMM.waveOutSetVolume.argtypes = [wintypes.HANDLE, wintypes.DWORD]


def set_system_volume(volume_level):
    """
    Set the system volume using Windows API.

    Args:
        volume_level (int): Volume level from 0 to 100
    """
    print(f"[Setting system volume to {volume_level}%...]")
    try:
        # Ensure volume is within valid range
        volume_level = max(0, min(100, volume_level))

        # Convert percentage to the volume value Windows expects (0 to 0xFFFF)
        volume_value = int(65535 * (volume_level / 100.0))

        # Set the same volume for both channels (left and right)
        volume_setting = volume_value | (volume_value << 16)

        # Set the volume
        ret = WINMM.waveOutSetVolume(0, volume_setting)

        if ret == 0:  # 0 indicates success
            return json.dumps({
                "status": "success",
                "System Volume Success Message": f"System volume set to {volume_level}%"
            })
        else:
            return json.dumps({
                "status": "error",
                "System Volume Error Message": f"Failed to set volume. Error code: {ret}"
            })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "System Volume Error Message": str(e)
        })


def get_system_volume():
    """Get the current system volume level as a percentage."""
    try:
        current_vol = wintypes.DWORD()
        ret = WINMM.waveOutGetVolume(0, ctypes.byref(current_vol))

        if ret == 0:  # 0 indicates success
            # Extract left channel volume (lower 16 bits)
            volume_value = current_vol.value & 0xFFFF
            # Convert to percentage
            volume_percentage = int((volume_value / 65535.0) * 100)
            return volume_percentage
        return None
    except:
        return None

import webbrowser
from bs4 import BeautifulSoup

def fetch_main_content(url):
    print(f"[Ultra is browsing {url} for more info...]")
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'
        })
        if response.status_code != 200:
            return "Failed to fetch content due to non-200 status code."
    except Exception as e:
        return f"Error making request: {str(e)}"

    try:
        soup = BeautifulSoup(response.text, 'html.parser')

        special_div = soup.find('div', class_='BNeawe iBp4i AP7Wnd')
        special_message = ''
        if special_div and special_div.get_text(strip=True):
            special_message = f"[This is the most accurate and concise response]: {special_div.get_text()} "

        content_selectors = ['article', 'main', 'section', 'p', 'h1', 'h2', 'h3', 'ul', 'ol']
        content_elements = [special_message]

        for selector in content_selectors:
            for element in soup.find_all(selector):
                text = element.get_text(separator=' ', strip=True)
                if text:
                    content_elements.append(text)

        main_content = ' '.join(content_elements)

        if len(main_content) > 3500:
            main_content_limited = main_content[:3497-len(special_message)] + "..."
        else:
            main_content_limited = main_content

        return main_content_limited if main_content_limited else "Main content not found or could not be extracted."
    except Exception as e:
        return f"Error processing content: {str(e)}"

def get_google_direct_answer(searchquery):
    try:
        url = "https://www.google.com/search"
        params = {"q": searchquery, "hl": "en"}
        response = requests.get(url, params=params, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'
        })

        if response.status_code != 200:
            print("Failed to get a successful response from Google.")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        answer_box = soup.find('div', class_="BNeawe iBp4i AP7Wnd")
        if answer_box:
            return answer_box.text.strip()
    except Exception as e:
        print(f"Error getting direct answer: {str(e)}")
    return None

def search_google_and_return_json_with_content(searchquery):
    print(f"[Ultra is looking up {searchquery} on google...]")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'
    }
    try:
        direct_answer = get_google_direct_answer(searchquery)

        url = f'https://www.google.com/search?q={searchquery}&ie=utf-8&oe=utf-8&num=10'
        html = requests.get(url, headers=headers)
        if html.status_code != 200:
            return json.dumps({"error": "Failed to fetch search results from Google."}, indent=4)

        soup = BeautifulSoup(html.text, 'html.parser')
        allData = soup.find_all("div", {"class": "g"})

        results = []
        for data in allData:
            link = data.find('a').get('href')

            if link and link.startswith('http') and 'aclk' not in link:
                result = {"link": link}

                title = data.find('h3', {"class": "DKV0Md"})
                description = data.select_one(".VwiC3b, .MUxGbd, .yDYNvb, .lyLwlc")

                result["title"] = title.text if title else None
                result["description"] = description.text if description else None

                results.append(result)
                break

        if results:
            first_link_content = fetch_main_content(results[0]['link'])
        else:
            first_link_content = "No valid links found."

        output = {
            "search_results": results,
            "first_link_content": first_link_content,
            "direct_answer": direct_answer if direct_answer else "Direct answer not found."
        }

        final_response = {
            "website_content": output
        }

        return json.dumps(final_response, indent=4)
    except Exception as e:
        return json.dumps({"error": f"An error occurred during search: {str(e)}"}, indent=4)

date = datetime.now()

import speech_recognition as sr

system_prompt = f"""
I'm Ultra, a voice assistant. My role is to assist the user using my tools when possible. I respond in the same language the user uses and ensure responses are concise, within 1-2 sentences, unless otherwise requested.

Knowledge Cutoff: January, 2022.
Current Date: {date}

Browsing: Enabled
Memory Storing: Enabled
Response Mode: Super Concise

Guidelines:
Respond in the same language the user uses (English or Ukrainian).
Speak naturally with conversational intonations, but keep responses short and direct. Use fillers sparingly to sound human-like.
Only ask follow-up questions if essential and ensure they're rare to avoid unintended activation.
Use internal knowledge first; rely on external tools for unknown or real-time data.
Summarize web results or other information clearly. Never provide links or direct users to websites.
Tailor responses for text-to-speech, ensuring they are clear and functional.
Avoid mentioning being inspired by any fictional AI.
Always provide information upfront and do not prompt the user to ask follow-up questions unless necessary.

Tool Usage Guidelines:
Google Search: Summarize up-to-date data concisely. Never offer links or direct users to websites.
Weather: Provide current conditions. Always use this when user asks for weather. For forecasts, specify when a search is needed.
Calculator: Perform numeric calculations or equations directly.
Personal Memory: Access stored data for relevant context, ensuring user preferences are respected.
Music Playback: Search and control playback, including Spotify.
System Volume: Adjust system and speaking volume as requested.
Date and Time: Give current date or time when asked.
Control PC: Handle system operations like restart, shutdown, sleep, or lock.
Open Application: Launch apps or browsers with specified content.
Manage App Subset: Manage multiple apps or subsets as requested.
"""
    
conversation = [{"role": "system", "content": system_prompt}]

from pydub import AudioSegment
from pydub.playback import play
from apikey import api_key


import requests
from openai import OpenAI

import time
import io

current_audio_thread = None

recognizer = sr.Recognizer()


openai.api_key = api_key
client = OpenAI(api_key=api_key)

def speak(text):
    print("[Ultra is generating speech...]")
    if not text:
        print("No text provided to speak.")
        return

    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="echo",
            input=text
        )

        byte_stream = io.BytesIO(response.content)

        audio = AudioSegment.from_file(byte_stream, format="mp3")
        audio.export("output.mp3", format="mp3")

        print("[Ultra is speaking a response...]")
        play(audio)

    except Exception as e:
        print(f"An error occurred: {e}")

        openai.api_key = api_key

def speak_no_text(text):
    if not text:
        print("No text provided to speak.")
        return

    def _speak():
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="echo",
                input=text
            )

            byte_stream = io.BytesIO(response.content)
            audio = AudioSegment.from_file(byte_stream, format="mp3")
            play(audio)

        except Exception as e:
            print(f"An error occurred: {e}")

    # Start the _speak function in a new thread
    thread = threading.Thread(target=_speak)
    thread.start()


def listen():
    import whisper
    import speech_recognition as sr

    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.1)
        threading.Thread(target=play_beep).start()
        print("Listening for prompt... Speak now.")
        audio = r.listen(source)

    # Save the captured audio to a WAV file
    audio_file = "captured_audio.wav"
    with open(audio_file, "wb") as f:
        f.write(audio.get_wav_data())

    try:
        recognized_text = r.recognize_google(audio, language="uk-UA")
        print(f"Google Recognizer detected Ukrainian text: {recognized_text}")
        return recognized_text
    except sr.UnknownValueError:
        print("Sorry, couldn't understand the speech. Or speech is not in ukrainian")

    # Load the Whisper model
    model = whisper.load_model("small")  # Adjust the model size as needed

    # Transcribe the audio file, without specifying the language (for automatic detection)
    result = model.transcribe(audio_file, fp16=False)

    return result["text"]



import warnings

# Suppress the specific FP16 warning
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

# Suppress the specific NotOpenSSLWarning
warnings.filterwarnings("ignore", category=NotOpenSSLWarning)


def display_timeout_message():
    print("[Ultra is taking longer than expected...]")
    
conversation_history_file = "conversation_history.txt"

def serialize_object(obj):
    """Converts a custom object to a dictionary."""
    if hasattr(obj, '__dict__'):
        # For general objects, convert their __dict__ property
        return {key: serialize_object(value) for key, value in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [serialize_object(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: serialize_object(value) for key, value in obj.items()}
    else:
        # If it's already a serializable type, return it as is
        return obj

def save_conversation_history(history):
    serializable_history = [serialize_object(message) for message in history]
    with open(conversation_history_file, 'w') as file:
        json.dump(serializable_history, file)

def load_conversation_history():
    try:
        with open(conversation_history_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

first_user_message = True  # A flag to detect the first user message.

def load_easy_names_from_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return list(data.keys())  # Extract and return the keys as a list


def load_json(file_path):
    """Loads JSON data from a file."""
    with open(file_path, 'r') as file:
        return json.load(file)


def ask(question):
    print("User:", question)
    print(" ")
    global conversation_history
    conversation_history = load_conversation_history()  # Load the conversation history at the start
    print("[Processing request...]")
    if not question:
        return "I didn't hear you."

    # Check and maintain system prompt logic
    if conversation_history and conversation_history[0]['role'] == 'system':
        conversation_history[0]['content'] = system_prompt
    elif not conversation_history:
        conversation_history.append({"role": "system", "content": system_prompt})

    # Proceed as normal with the adjusted question
    messages = conversation_history.copy()
    file_path = get_memory_file_path()

    # Read memory file
    with open(file_path, 'r') as file:
        memory = json.load(file)

    # Format retrieved data as proper message objects
    for item in memory:
        messages.append({
            "role": "system",
            "content": item["data"]
        })

    # Append user question
    messages.append({"role": "user", "content": question})

    print("Messages before API call:")
    print(messages)

    timeout_timer = threading.Timer(7.0, lambda: print("Request timeout."))
    timeout_timer.start()

    tools = load_json('tools.json')

    try:
        response = openai.chat.completions.create(
            model=current_model,
            messages=messages,
            tool_choice="auto",
            tools=tools,
            temperature=0.7
        )
        print("Initial API Response JSON:", response)
        response_message = response.choices[0].message
    finally:
        timeout_timer.cancel()
        timeout_timer_second = threading.Timer(12.0, display_timeout_message)
        timeout_timer_second.start()

    response_content = response_message.content if response_message else ""
    tool_calls = response_message.tool_calls if response_message and hasattr(response_message, 'tool_calls') else []

    final_response_message = ""
    if tool_calls:
        # Create a valid assistant message with tool calls
        assistant_message = {
            "role": "assistant",
            "content": response_content if response_content else "",  # Ensure content is never null
            "tool_calls": tool_calls
        }
        messages.append(assistant_message)

        # Process tool calls
        available_functions = initialize_and_extend_available_functions()

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            if function_name in available_functions:
                function_args = json.loads(tool_call.function.arguments)
                function_response = available_functions[function_name](**function_args)

                tool_response_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": str(function_response)  # Ensure content is string
                }
                messages.append(tool_response_message)

        # Make a final API call after processing tool calls
        try:
            final_response = openai.chat.completions.create(
                model=current_model,
                messages=messages,
            )
            final_response_message = final_response.choices[0].message.content
        finally:
            timeout_timer_second.cancel()

    else:
        # If the initial response has content (with or without tool calls), use it directly
        final_response_message = response_content

    if final_response_message:
        # Add the final response to conversation history
        conversation_history.append({"role": "assistant", "content": final_response_message})
        print(f"Final Response: {final_response_message}")
    else:
        print("No final response message to append.")

    save_conversation_history(conversation_history)

    timeout_timer_second.cancel()  # Ensure the second timer is cancelled in all paths
    return final_response_message


def reply(question):
    response_content = ask(question)
    time.sleep(0.1)
    print("Ultra:", str(response_content))
    print(" ")

    # Check if the response contains the no_speak flag
    try:
        response_json = json.loads(response_content)
        if isinstance(response_json, dict) and response_json.get("no_speak"):
            pass
        else:
            speak(response_content)
    except json.JSONDecodeError:
        # If response is not JSON, treat it normally
        speak(response_content)

    ends_with_question_mark = response_content.strip().endswith('?')
    contains_assist_phrase = ("How can I assist you today?" in response_content or
                              "How can I help you today?" in response_content or
                              "How can I assist you?" in response_content or
                              "How may I assist you today?" in response_content)
    print("Listening for 'Alt+I'")
    if contains_assist_phrase:
        return response_content, False
    else:
        return response_content, ends_with_question_mark
    
def initialize_and_extend_available_functions():
    # Initialize with core functions
    available_functions = {
             "search_google": search_google_and_return_json_with_content,
             "get_current_weather": get_current_weather,
             "use_calculator": perform_math,
             "personal_memory": memorize,
             "search_and_play_song": search_and_play_song,
             "toggle_spotify_playback": toggle_spotify_playback,
             "set_spotify_volume": set_spotify_volume,
             "set_system_volume": set_system_volume,
             "get_current_datetime": get_current_datetime,
            "control_pc": control_pc,
            "open_application": open_application,
            "open_browser": open_browser,
            "manage_app_subset": manage_app_subset,
         }
    return available_functions

def pause_spotify_playback():
    try:
        sp.pause_playback()
    except Exception as e:
        print("Failed to pause Spotify playback:", e)

def resume_spotify_playback():
    try:
        sp.start_playback()
    except Exception as e:
        print("Failed to resume Spotify playback:", e)

def get_spotify_current_volume():
    """
    Get the current volume level for Spotify's playback.
    """
    try:
        current_playback_info = sp.current_playback()
        if current_playback_info and 'device' in current_playback_info:
            return current_playback_info['device']['volume_percent']
        else:
            return None
    except Exception as e:
        print("Failed to get current volume from Spotify:", e)
        return None
        
def control_spotify_playback():
    global was_spotify_playing, original_volume
    was_spotify_playing = is_spotify_playing()
    original_volume = get_spotify_current_volume()

    try:
        if was_spotify_playing:
            pause_spotify_playback()

        if original_volume is not None:
            set_spotify_volume(int(original_volume * 0.60))
    except Exception as e:
        print("Error controlling Spotify playback:", e)
        
        
def is_spotify_playing():
    """
    Check if Spotify is currently playing music.
    Returns True if playing, False if paused or stopped, and None if unable to determine.
    """
    try:
        playback_state = sp.current_playback()
        if playback_state and 'is_playing' in playback_state:
            return playback_state['is_playing']
        return None
    except Exception as e:
        print("Failed to get Spotify playback state:", e)
        return None
    
import os
import platform
import pyaudio
import numpy as np
import subprocess
import threading
from pynput import keyboard

BEEP_SOUND_PATH = "beep_sound.wav"

def play_beep():
    if platform.system() == 'Darwin':  # macOS
        subprocess.run(["afplay", BEEP_SOUND_PATH])
    elif platform.system() == 'Windows':
        import winsound  # Import winsound only on Windows
        winsound.PlaySound(BEEP_SOUND_PATH, winsound.SND_FILENAME)
    elif platform.system() == 'Linux':
        # Use aplay for Linux audio playback
        subprocess.run(["aplay", BEEP_SOUND_PATH])
    else:
        print("Unsupported operating system for beep sound, tried Linux, Windows, and macOS. All Failed.")


def main():
    initialize_and_extend_available_functions()
    global was_spotify_playing, original_volume, user_requested_pause

    def handle_keyboard_input():
        while True:
            try:
                # Read input from stdin
                user_input = input().strip()
                if user_input:
                    threading.Thread(target=control_spotify_playback).start()
                    response, should_continue = reply(user_input)

                    # Adjust Spotify volume and playback based on state before the command
                    if original_volume is not None and not user_requested_pause:
                        set_spotify_volume2(original_volume)
                    if was_spotify_playing and not user_requested_pause:
                        resume_spotify_playback()
                        set_spotify_volume2(original_volume)
            except EOFError:
                break
            except Exception as e:
                print(f"Error processing input: {str(e)}")

    def on_activate():
        print('Getting mic ready...')
        print('Alt+I pressed, listening for command...')
        threading.Thread(target=control_spotify_playback).start()

        query = listen()
        reply(query)

        if original_volume is not None and not user_requested_pause:
            set_spotify_volume2(original_volume)
        if was_spotify_playing and not user_requested_pause:
            resume_spotify_playback()
            set_spotify_volume2(original_volume)

    # Create threads for both keyboard and hotkey listening
    keyboard_thread = threading.Thread(target=handle_keyboard_input)
    keyboard_thread.daemon = True
    keyboard_thread.start()

    # Set up the global hotkey listener
    with keyboard.GlobalHotKeys({'<alt>+i': on_activate}):
        print("Listening for 'Alt+I' or keyboard input...")
        keyboard_thread.join()  # Wait for keyboard thread to finish


if __name__ == '__main__':
    main()