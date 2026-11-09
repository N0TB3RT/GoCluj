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

Răspuns HTTP 200, JSON: un array de evenimente. `[]` înseamnă că nu există evenimente. Obiectele de paginare nu fac parte din contractul S0 implementat.

```json
[
  {
    "id": 1,
    "title": "Titlul evenimentului",
    "event_date": "2026-11-12T19:30:00+02:00",
    "location_name": "Locația evenimentului",
    "price_info": "50 lei",
    "is_free": false,
    "source_url": "https://organizator.example/eveniment"
  }
]
```

Acesta este doar un exemplu de contract; aplicația nu îl încarcă. Sunt acceptate și câmpurile `start_time`, `venue`, `price` din cerință. `is_free: true` sau `price: 0` afișează „Gratuit”; un preț absent nu este presupus gratuit. Timestamp-urile cu fus orar sunt afișate în `Europe/Bucharest`; cele fără offset păstrează ora furnizată. Backend-ul ar trebui să emită ISO 8601 cu offset. Linkurile sursă acceptă numai HTTP(S), se deschid în filă nouă și au `noopener noreferrer`.

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
