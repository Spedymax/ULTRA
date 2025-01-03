# app_paths.py

APP_PATHS = {
    'windows': {
        'chrome': {
            'common_name': ['chrome', 'google chrome'],
            'paths': [
                r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
            ]
        },
        'firefox': {
            'common_name': ['firefox', 'mozilla firefox'],
            'paths': [
                r'C:\Program Files\Mozilla Firefox\firefox.exe',
                r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe'
            ]
        },
        'edge': {
            'common_name': ['edge', 'microsoft edge'],
            'paths': [
                r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
            ]
        },
        'spotify': {
            'common_name': ['spotify'],
            'paths': [
                r'C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe',
                r'%APPDATA%\Spotify\Spotify.exe'
            ]
        },
        'telegram': {
            'common_name': ['telegram'],
            'paths': [
                r"C:\\Users\\Spedy\\AppData\\Roaming\\Telegram Desktop\\Telegram.exe"
            ]
        }
    }
}