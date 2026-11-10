# GoCluj frontend — PRJ-00 / Sprint 0

React + Vite. Lista afișează exclusiv evenimentele returnate de backend, fără date demonstrative de rezervă. Tema întunecată, logo-ul alb și fotografia Clujului sunt păstrate. Filtrele și categoriile sunt amânate pentru S1.

## Pornire locală

Din `frontend`:

```sh
npm ci
npm run dev
```

Deschide http://localhost:3000. Implicit, clientul cere `/api/events`, iar Vite trimite cererea către `http://localhost:8000/api/events`. Backend-ul trebuie pornit separat.

Opțional, copiază `.env.example` în `.env.local` și repornește Vite după modificări:

- `VITE_API_URL`: baza publică a API-ului, fără `/api/events` la final. Clientul apelează `GET ${import.meta.env.VITE_API_URL}/api/events`; valoarea absentă sau goală înseamnă aceeași origine (`/api/events`). Exemplu direct: `http://localhost:8000`. Nu introduce secrete în variabile `VITE_*`.
- `API_PROXY_TARGET`: destinația folosită doar de serverul Vite când `VITE_API_URL` este goală. Implicit `http://localhost:8000`.

Apelul direct către altă origine necesită CORS în backend. Proxy-ul Vite evită această cerință pentru dezvoltare și pentru configurația Docker actuală. `REACT_APP_API_URL` nu este utilizată.

## Docker Compose

Dockerfile-ul frontend setează `VITE_API_URL` goală și `API_PROXY_TARGET=http://backend:8000`. Astfel, configurația Compose existentă poate folosi proxy-ul fără schimbări în fișierul de la rădăcină. Browserul nu trebuie să rezolve numele Docker `backend`.

După actualizarea frontend-ului, rulează de la rădăcina proiectului:

```sh
docker compose up --build
```

Un eventual fișier local `.env.local` montat în container poate schimba `VITE_API_URL`; verifică-l dacă vrei să folosești proxy-ul implicit. Variabilele din mediul procesului au prioritate.

Pentru publicarea unui build static, `VITE_API_URL` se stabilește la build. Dacă rămâne goală, serverul care găzduiește `dist` trebuie să redirecționeze `/api` către backend; proxy-ul Vite nu este inclus în fișierele statice.

## Contract GET /api/events

`GET /api/events?limit=20&offset=0` returns HTTP 200 with a page of upcoming events, sorted by start time. The client asks for 20 events at a time and the "Încarcă mai multe" button requests the next page with `offset = number of events already loaded` while that number is below `total`. `items: []` with `total: 0` means there are no events. Any other shape (a bare array, a missing `items` array, a non-numeric `total`) is treated as an invalid response and shown as an error.

```json
{
  "items": [
    {
      "id": 12,
      "source_name": "LiveTickets",
      "source_url": "https://www.livetickets.ro/bilete/balul-dintilor-de-lapte-1",
      "title": "Balul “Dinților de Lapte”",
      "description": "Line one\n\nLine two",
      "start_at": "2026-11-12T21:00:00+02:00",
      "end_at": "2026-11-13T05:00:00+02:00",
      "venue": { "name": "MATTER", "address": "Str. Universității 3", "city": "Cluj-Napoca", "lat": 46.768, "lng": 23.590 },
      "price_text": "30 - 35 RON",
      "is_free": false,
      "categories": [],
      "source_category": "divertisment",
      "image_url": "https://cdn.example/x/Background_MEDIUM.jpg"
    }
  ],
  "total": 31,
  "limit": 20,
  "offset": 0
}
```

`description`, `end_at`, every `venue` field, `price_text`, `is_free`, `source_category` and `image_url` may be `null`.

`GET /api/events/{id}` returns one event object with the same shape, or HTTP 404 `{"detail": "Event not found"}`. The client reports a 404 with the distinct error code `not-found` and shows "Evenimentul nu a fost găsit.".

Frontend routes: `/` is the home page with the event list; `/evenimente/:id` is the event detail page (`EventDetailPage`). The Vite dev server falls back to `index.html` for client routes; a static host must do the same for `/evenimente/*`.

Client rules:

- The event is normalized to `{ id, key, title, description, startAt, endAt, venueName, venueAddress, price, sourceName, sourceUrl, imageUrl }`.
- Price: `is_free === true` shows "Gratuit"; otherwise `price_text`, otherwise "Preț neprecizat". Free admission is never assumed.
- `source_url` and `image_url` are accepted only when they are absolute HTTP(S) URLs. Source links open in a new tab with `noopener noreferrer`; external images use `referrerPolicy="no-referrer"`. A missing or broken image is replaced by a placeholder.
- Timestamps with an offset are shown in `Europe/Bucharest`; timestamps without an offset keep the provided wall-clock time. When `end_at` is later than `start_at` a range is shown ("12 noiembrie 2026, 21:00 – 23:00" on the same day, otherwise both dates).
- The description is rendered as plain text (`white-space: pre-line`), never as HTML.

## Stări și verificări

- Loading real cât timp se așteaptă răspunsul API, cu animație care respectă preferința pentru mișcare redusă.
- Eroare pentru HTTP nereușit, rețea, JSON/format invalid și timeout de 15 secunde; buton de reîncercare.
- Stare distinctă pentru listă goală, plus actualizare manuală după rularea scraper-ului.
- Anularea cererilor la demontarea componentei, inclusiv în React StrictMode.

```sh
npm test
npm run lint
npm run build
```

Testele verifică clientul API, adaptarea câmpurilor, linkurile, datele și randarea stărilor/cardurilor. Răspunsurile simulate din teste nu sunt incluse în lista afișată de aplicație.

## Dependențe externe rămase pentru demo

La verificarea acestui checkout, `backend/main.py` definește numai POST `/api/events`, fără GET. Echipa backend trebuie să adauge GET public care citește evenimentele din baza de date și returnează array-ul de mai sus. Până atunci frontend-ul afișează eroarea HTTP și permite reîncercarea.

Scraper-ul actual trimite un singur „Concert Test Cluj” cu o sursă de exemplu. Echipa scraper trebuie să furnizeze evenimente reale. Nu s-au modificat backend-ul, scraper-ul sau Compose în această intervenție.

Verificarea finală: pe un checkout curat, configurați mediul cerut de Compose, porniți serviciile, rulați scraper-ul, apoi apăsați „Actualizează lista”. Verificați titlul, data, locația, prețul și sursa originală pentru evenimentele persistate. Opriți backend-ul pentru verificarea erorii, reporniți-l și reîncercați. Testele frontend nu substituie această probă end-to-end.
