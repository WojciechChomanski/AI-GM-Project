# PROJECT_CONTEXT.md
## Zentrales Wissens- und Entscheidungsdokument für das AI-GM-Projekt

**Stand:** 03. Juni 2026  
**Aktueller Fokus:** Wrath & Glory One-Shot „Operation Black Veil“  
**Ziel dieser Datei:** Langfristiges Projektgedächtnis für Wrath & Glory **und** das Fantasy-Hauptprojekt. Wissen, Entscheidungen und Erfahrungen sollen nicht verloren gehen und später wiederverwendet werden können.

---

### 1. Projektlandschaft

#### 1.1 Wrath & Glory One-Shot: „Operation Black Veil“
- **Genre:** Grimdark Warhammer 40k (Wrath & Glory)
- **Setting:** Convent of the Ghoul Veil (Order of the Ghoul Veil) am Rande der Ghoul Stars
- **Kernkonflikt:** Die Spieler geraten in einen Standoff zwischen:
  - Adepta Sororitas (Order of the Ghoul Veil) → teilweise von einem Genestealer Cult infiltriert
  - Imperialer Armee (Cadian 92nd unter Sergeant Torvax)
  - Inquisition (Interrogator Veyra Kane)
- **Zentrale Themen:** Loyalität vs. Zweifel, verborgene Korruption, moralische Grauzonen, Genestealer-Infiltration durch Waisenprogramm
- **Wichtige NPCs:** 6 zentrale Charaktere (siehe Abschnitt 3)

#### 1.2 Fantasy-Hauptprojekt (AI-GM-Project Main Branch)
- Grimdark Fantasy mit eigenem System („Breath and Veil“)
- Fokus auf tiefgehende NPC-Entwicklung, dynamische Beziehungen und langfristige Weltentwicklung
- Ziel: Wiederverwendung von Erfahrungen, Strukturen und Techniken aus dem Wrath & Glory Projekt

**Verbindung der beiden Projekte:**  
Viele Konzepte (NPC-Entwicklung, Guard Rails, Memory-System, Charakter-Erkennung, innere Konflikte, sprachliche Differenzierung) sollen langfristig in beiden Projekten wiederverwendet werden.

---

### 2. Aktueller Technischer Stack (Wrath & Glory)

- **Backend:** `chat_api_wng.py` (FastAPI + Grok-3 API)
- **Memory-System:** Pro-NPC Memory-Dateien im Ordner `memory/`
- **NPC-Daten:** JSON-Dateien im Ordner `npcs/wrath-and-glory/`
- **Frontend:** Foundry VTT mit individuellen Makros pro NPC
- **Wichtige Dateien:**
  - `chat_api_wng.py` (aktuelle Version mit verbesserter `load_npc`-Funktion)
  - `PROJECT_CONTEXT.md` (diese Datei)

---

### 3. Wichtige NPCs (Stand Juni 2026)

#### 3.1 Sister Hospitaller Lirien (aktuell schwierigster NPC)
- **Kernproblem:** Innere Zerrissenheit zwischen Loyalität zu Veridya und wachsenden Zweifeln am Vorgehen des Konvents
- **Aktueller Stand:** Guard Rails und `speech_style` mehrfach überarbeitet (Version 1.7)
- **Zielverhalten:** Starkes Zögern, Unwohlsein, Vermeidung klarer Positionen, emotionale Belastung
- **Offen:** Weitere Feinabstimmung notwendig

#### 3.2 Sergeant Torvax “Ironjaw”
- **Charaktergrundlage:** Harter, zynischer, ungefilterter Cadian-Veteran (inspiriert von Predator-Charakteren)
- **Wichtige Eigenschaften:** Misstrauen gegenüber den Schwestern, Trauma durch verlorenes Regiment, bittere Direktheit
- **Aktueller Stand:** Akzeptabel bis gut. Direktheit und Grobheit sind gewollt.

#### 3.3 Weitere NPCs
- **Sister Superior Veridya**: Fanatisch, selbstgerecht, manipuliert (frühe Genestealer-Hybrid)
- **Interrogator Veyra Kane**: Kalt, berechnend, eloquent, gefährlich
- **The Silent One (K-17)**: Gebrochen, still, traumatisiert, poetisch-verstört
- **Cult Magus “Father”**: Sanft, väterlich-manipulativ, verstörend freundlich (bester NPC aktuell)

---

### 4. Wichtige Design-Prinzipien & Entscheidungen

#### 4.1 NPC-Entwicklung
- NPCs sollen **unterschiedlich auf unterschiedliche Charaktere** reagieren (Space Marine vs. normaler Mensch, Mann vs. Frau, etc.)
- Starke Betonung von **inneren Konflikten** (besonders bei Lirien)
- Guard Rails sollen nicht nur Ton und Lore, sondern auch **konkretes Verhalten** steuern
- Speech Style und Quirks sind mindestens genauso wichtig wie die eigentlichen Guard Rails

#### 4.2 Technische Architektur
- Separate `chat_api_wng.py` für das Wrath & Glory Projekt (saubere Trennung vom Fantasy-Projekt)
- Memory-System pro NPC (Datei-basiert)
- Foundry VTT als primäres Frontend mit individuellen Makros

#### 4.3 Langfristige Ziele
- NPCs sollen Charakter-Typ (Rasse, Geschlecht, Klasse/Rolle) erkennen und entsprechend unterschiedlich reagieren
- Wissen und Erfahrungen aus dem Wrath & Glory Projekt sollen systematisch ins Fantasy-Hauptprojekt übertragen werden können
- Langfristig: Ein stabiles, projektübergreifendes NPC- und Memory-System

---

### 5. Offene Themen & Bekannte Probleme (Stand 03.06.2026)

- **Lirien**: Innerer Konflikt noch nicht stark genug konsistent umgesetzt
- **Charakter-Erkennung**: Noch nicht implementiert (wichtiges zukünftiges Feature)
- **Memory-System**: Funktioniert, aber noch relativ einfach (nur Impressions + letzte Interaktion)
- **Cross-Projekt-Wissen**: Noch keine strukturierte Übertragung zwischen Wrath & Glory und Fantasy-Projekt

---

### 6. Arbeitsweise mit Grok / KI

Diese Datei (`PROJECT_CONTEXT.md`) soll bei jeder größeren Arbeitsphase mit einbezogen werden, damit:

- Wichtige Entscheidungen und der aktuelle Projektstand bekannt sind
- Der Stil und die Philosophie des Projekts eingehalten werden
- Wissen nicht verloren geht

**Empfohlene Vorgehensweise:**
1. Am Anfang einer neuen Arbeitsphase diese Datei mit einlesen
2. Nach wichtigen Änderungen oder Entscheidungen diese Datei aktualisieren
3. Bei komplexen Themen (z. B. neue NPC-Features) diese Datei als Referenz nutzen

---

### 7. Zukunftsvision

Dieses Dokument soll langfristig dazu dienen, dass:

- Erfahrungen aus dem Wrath & Glory One-Shot systematisch ins Fantasy-Hauptprojekt übernommen werden können
- Techniken (Guard Rails, Speech Style, Memory, Charakter-Erkennung) projektübergreifend weiterentwickelt werden
- Das Wissen auch in 6–12 Monaten noch verfügbar ist, auch wenn zwischenzeitlich Pausen entstehen

---

**Letztes Update:** 03. Juni 2026  
**Nächste geplante Aktualisierung:** Nach Abschluss der aktuellen Lirien-Überarbeitung + Implementierung der Charakter-Erkennung