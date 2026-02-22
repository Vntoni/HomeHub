"""
TEMPLATE - Wklej tutaj dane z mitmproxy i przetestuj endpoint
"""
import requests
import json

# ============================================================================
# WKLEJ TUTAJ DANE Z mitmproxy (po przechwyceniu ruchu)
# ============================================================================

# URL który znalazłeś w mitmproxy
ENDPOINT = "https://ZMIEN_NA_PRAWDZIWY_URL/login"

# Credentials
USERNAME = "antekmigala@gmail.com"
PASSWORD = "F5eotvky"

# Headers (skopiuj z mitmproxy jeśli są jakieś specjalne)
HEADERS = {
    'Content-Type': 'application/json',  # lub 'application/x-www-form-urlencoded'
    'User-Agent': 'ZMIEN_JESLI_POTRZEBA',
}

# Body - format może być JSON lub form-data
# Sprawdź w mitmproxy jaki format używa aplikacja!

# OPCJA 1: JSON body (jeśli Content-Type: application/json)
REQUEST_BODY_JSON = {
    "email": USERNAME,      # Może być "email", "userId", "username"
    "password": PASSWORD,   # Może być "password", "userPassword", "pwd"
    # Dodaj inne pola jeśli są wymagane:
    # "deviceId": "...",
    # "apiKey": "...",
}

# OPCJA 2: Form data (jeśli Content-Type: application/x-www-form-urlencoded)
REQUEST_BODY_FORM = {
    'userId': USERNAME,
    'userPassword': PASSWORD,
}

# ============================================================================
# TEST POŁĄCZENIA
# ============================================================================

print("=" * 80)
print(" TEST ENDPOINTU ATLANTIC COZY TOUCH")
print("=" * 80)

print(f"\nEndpoint: {ENDPOINT}")
print(f"Username: {USERNAME}")
print(f"Password: {'*' * len(PASSWORD)}\n")

# Wybierz odpowiednią opcję (JSON lub FORM):

# TEST 1: JSON
print("TEST 1: POST z JSON body")
print("-" * 80)
try:
    response = requests.post(
        ENDPOINT,
        json=REQUEST_BODY_JSON,  # <-- JSON
        headers=HEADERS,
        timeout=30
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        print("\n✓✓✓ SUCCESS! Połączenie działa!")
        print("\nResponse:")
        print(json.dumps(response.json(), indent=2))

        # Zapisz token jeśli jest
        data = response.json()
        if 'token' in data or 'access_token' in data or 'accessToken' in data:
            token = data.get('token') or data.get('access_token') or data.get('accessToken')
            print(f"\n✓ Token: {token[:50]}...")

    elif response.status_code == 401:
        print("\n✗ Błąd autoryzacji (401)")
        print(response.text)
        print("\nSprawdź:")
        print("  - Czy URL jest poprawny?")
        print("  - Czy nazwy pól są poprawne? (email vs userId)")
        print("  - Czy format jest poprawny? (JSON vs form-data)")

    else:
        print(f"\n? Status: {response.status_code}")
        print(response.text[:500])

except requests.exceptions.ConnectionError:
    print("\n✗ Connection Error - sprawdź URL")
except Exception as e:
    print(f"\n✗ Error: {e}")

# TEST 2: Form data (jeśli JSON nie zadziała)
print("\n\n" + "=" * 80)
print("TEST 2: POST z form data")
print("-" * 80)
try:
    response = requests.post(
        ENDPOINT,
        data=REQUEST_BODY_FORM,  # <-- Form data
        headers={'User-Agent': HEADERS.get('User-Agent', 'Mozilla/5.0')},
        timeout=30
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        print("\n✓✓✓ SUCCESS! Połączenie działa!")
        print("\nResponse:")
        print(json.dumps(response.json(), indent=2))

    elif response.status_code == 401:
        print("\n✗ Błąd autoryzacji (401)")
        print(response.text)

    else:
        print(f"\n? Status: {response.status_code}")
        print(response.text[:500])

except Exception as e:
    print(f"\n✗ Error: {e}")

print("\n" + "=" * 80)
print(" INSTRUKCJE")
print("=" * 80)
print("""
Jeśli test zadziałał (status 200):
✓ Mamy działający endpoint!
✓ Możemy go zintegrować z projektem!

Następne kroki:
1. Zapisz dane endpointu (URL, format, headers)
2. Dostosuję adapter cozytouch_heater_adapter.py
3. Zintegruję z compositions.py
4. Przetestuję z prawdziwymi urządzeniami

---

Jeśli test NIE zadziałał:
✗ Sprawdź czy skopiowałeś DOKŁADNIE z mitmproxy:
  - URL (całe https://...)
  - Nazwy pól (email vs userId vs username)
  - Format (JSON vs form-data)
  - Headers (Content-Type!)

Wyślij mi screenshot z mitmproxy request/response!
""")

# ============================================================================
# HELPER - Sprawdzenie co jest w response
# ============================================================================

print("\n" + "=" * 80)
print(" HELPER - Analiza response")
print("=" * 80)
print("""
Po udanym logowaniu sprawdź w response:

1. Token/Session:
   - Może być: "token", "access_token", "accessToken", "jwt"
   - Zapisz go - będzie potrzebny do innych requestów

2. User ID:
   - Może być: "user_id", "userId", "id"

3. Inne dane:
   - Devices list?
   - API endpoints?
   - Refresh token?

Wszystko co widzisz w response - zapisz!
""")
