# 📚 Guida alle Mod del Pacchetto

Questo documento descrive tutte le mod presenti nel file `config.json`.
Le mod sono divise per categoria come nel file di configurazione.

---

## 🚀 Ottimizzazione (Performance & FPS)
*Mod che migliorano le prestazioni senza cambiare il gioco.*

*   **Sodium**: Motore di rendering che sostituisce quello vanilla. Aumenta drasticamente gli FPS.
*   **Sodium Extra**: Aggiunge opzioni grafiche avanzate a Sodium (particelle, meteo, ecc.).
*   **Reese's Sodium Options**: Ridisegna il menu delle impostazioni video di Sodium per renderlo più pulito.
*   **Lithium**: Ottimizza la fisica di gioco, l'IA dei mob e il tick del server (riduce il lag TPS).
*   **Indium**: Addon per Sodium che garantisce compatibilità con mod che usano rendering avanzato (es. BetterGrassify).
*   **Krypton**: Ottimizza lo stack di rete di Minecraft (riduce il lag online e l'uso della banda).
*   **FerriteCore**: Riduce drasticamente l'utilizzo della RAM.
*   **ModernFix**: Corregge bug del motore di gioco, velocizza l'avvio e riduce l'uso di RAM.
*   **ImmediatelyFast**: Ottimizza il rendering "immediato" (GUI, testi, mob) aumentando gli FPS.
*   **Dynamic FPS**: Riduce gli FPS quando il gioco è in background (Alt-Tab) per non surriscaldare il PC.
*   **More Culling**: Non renderizza le parti di blocchi nascoste che non vedi, risparmiando risorse.
*   **Entity Culling**: Nasconde entità e tile entity che non sono visibili dalla telecamera (enorme risparmio FPS).
*   **FastAnim**: Ottimizza il calcolo delle animazioni delle entità.
*   **Spark**: Profiler delle prestazioni per diagnosticare cause di lag e picchi di CPU/RAM.
*   **FastLoad**: Velocizza significativamente il caricamento dei mondi.
*   **ForgetMeChunk**: Corregge un memory leak che causa cali di FPS nel caricamento chunk.
*   **C2ME (Concurrent Chunk Management Engine)**: Genera i chunk usando tutti i core del processore.
*   **BadOptimizations**: Micro-ottimizzazioni per la gestione della luce e rendering entità.
*   **VMP (Very Many Players)**: Ottimizza il gioco in presenza di molti giocatori o entità.
*   **Enhanced Block Entities**: Ottimizza chest, letti e altri blocchi speciali.
*   **Memory Leak Fix**: Previene che la RAM si riempia all'infinito durante le sessioni lunghe.
*   **Noisium**: Ottimizza l'algoritmo di generazione del terreno.
*   **ThreadTweak**: Migliora la gestione dei thread della CPU.
*   **ServerCore**: Ottimizzazioni tecniche per il lato server.
*   **Exordium**: Ottimizza il rendering dell'interfaccia utente (GUI).
*   **Ksyxis**: Velocizza il caricamento del mondo non caricando gli spawn chunk inutilmente.
*   **Alternate Current**: Ottimizza il sistema della Redstone.
*   **Smooth Boot**: Riduce i freeze durante il caricamento iniziale del gioco.
*   **Cull Less Leaves**: Migliora le prestazioni delle foglie degli alberi.
*   **Clumps**: Raggruppa le sfere di esperienza in un unico ammasso per ridurre il lag.
*   **Get It Together, Drops!**: Raggruppa gli oggetti a terra per migliorare le prestazioni.
*   **TT20**: Ottimizzazione tecnica del tracking dei tick di gioco.
*   **LMD (Let Me Despawn)**: Migliora le performance despawnando i mob non necessari.
*   **Video Tape**: Ottimizza il rendering di video e animazioni nel gioco.
*   **Marlow's Crystal Optimizer**: Ottimizza il rendering e la logica degli End Crystal.
*   **Hero's Anchor Optimizer**: Ottimizza il blocco Ancora della Rinascita.

## 🎨 Grafica & Estetica
*Mod che rendono il gioco più bello.*

*   **Iris Shaders**: Permette di installare ed usare gli Shaders.
*   **3D Skin Layers**: Rende lo strato esterno della skin in 3D reale.
*   **Animatica**: Supporta texture animate (feature stile OptiFine).
*   **BetterGrassify**: Permette l'erba connessa per un terreno più naturale.
*   **Capes**: Permette di vedere i mantelli dei giocatori.
*   **Chat Heads**: Mostra la testa del giocatore in chat.
*   **Cubes Without Borders**: Corregge visivamente i bordi delle texture dei blocchi.
*   **LambDynamicLights**: La torcia in mano illumina l'area mentre cammini.
*   **Model Gap Fix**: Chiude i buchi nei modelli 3D di oggetti e mob.
*   **Not Enough Animations**: Aggiunge animazioni in terza persona realistiche.
*   **Puzzle / Optiboxes**: Supporto per skybox custom e altre feature grafiche avanzate.
*   **OptiGUI**: Permette interfacce (GUI) personalizzate tramite Resource Pack.
*   **Wakes**: Aggiunge scie d'acqua realistiche per le barche.
*   **Drip Sounds**: Aggiunge suoni e particelle quando l'acqua gocciola.
*   **Visuality / Particle Core**: Aggiunge particelle ambientali extra (lucciole, polvere).
*   **First Person Model**: Permette di vedere il proprio corpo in prima persona.

## 🛠️ Utilità (Quality of Life) Base
*Funzioni utili per l'interfaccia e il gameplay base.*

*   **AppleSkin**: Informazioni su fame e saturazione nell'HUD.
*   **Better Mount HUD**: Migliora la barra della vita della cavalcatura.
*   **Gamma-Utils**: Permette il Fullbright (vedere al buio) premendo un tasto.
*   **Inventory Profiles Next**: Ordina automaticamente inventari e casse.
*   **Mod Menu**: Menu per gestire e configurare le mod installate.
*   **More Chat History**: Aumenta la cronologia dei messaggi in chat.
*   **Remove Reloading Screen**: Rimuove la schermata di caricamento quando si cambiano i pack.
*   **YOSBR**: Protegge le impostazioni personalizzate dell'utente.
*   **Zoomify**: Aggiunge uno zoom fluido (tasto C).
*   **Controlify**: Supporto avanzato per i controller.
*   **Chunky**: Pre-generazione dei chunk per esplorazioni senza lag.
*   **Litematica**: Sistema di schematiche per costruzioni facilitate.
*   **Litematica-printer**: Addon per piazzare automaticamente i blocchi delle schematiche.
*   **Bobby**: Permette di vedere chunk oltre il limite del server salvandoli in locale.
*   **FastQuit**: Permette di uscire dai mondi istantaneamente salvando in background.
*   **Language Reload**: Ricarica le lingue del gioco molto velocemente.
*   **No Chat Reports**: Protegge la privacy disabilitando le segnalazioni chat di Microsoft.
*   **e4mc**: Permette di invitare amici nel proprio mondo LAN tramite internet senza configurare il router.
*   **Don't Drop It!**: Impedisce di gettare accidentalmente oggetti importanti a terra.
*   **Almanac**: Un'enciclopedia interattiva per consultare informazioni sulle mod.
*   **Smooth Scrolling / Smooth Swapping / Smooth Gui**: Rendono le animazioni dell'interfaccia molto più fluide.
*   **Shulker Box Tooltip**: Visualizza il contenuto delle Shulker Box passandoci sopra il mouse.

## 🌲 Survival QoL & Gameplay Mods
*Modifiche specifiche per migliorare l'esperienza Survival.*

*   **Nature's Compass**: Bussola speciale per localizzare i biomi.
*   **Explorer's Compass**: Bussola per trovare strutture (villaggi, piramidi, ecc.).
*   **Waystones**: Aggiunge pietre del teletrasporto per spostamenti rapidi tra basi.
*   **Traveler's Backpack**: Zaini funzionali che offrono inventario extra e utilità.
*   **Comforts**: Saggi a pelo e amache per dormire senza cambiare il punto di spawn.
*   **Terralith / Tectonic**: Migliorano drasticamente la generazione del mondo e dei biomi.
*   **Nullscape**: Rivoluziona la dimensione dell'End rendendola più varia.
*   **Farmers Delight Refabricated**: Espande il sistema di cucina e agricoltura.
*   **Falling Tree**: Permette di abbattere interi alberi rompendo un solo blocco.
*   **RightClick Harvest**: Raccolta e ripiantamento automatico dei raccolti col tasto destro.
*   **Trade Cycling**: Permette di cambiare le offerte dei Villager facilmente.
*   **RPG Difficulty**: Aumenta progressivamente la difficoltà del gioco.
*   **Trinkets**: Aggiunge nuovi slot per accessori indossabili (anelli, collane).
*   **Waystones**: Pietre miliari per il viaggio rapido.
*   **Advancement Plaques / Better Advancements**: Migliorano l'interfaccia e i pop-up dei progressi.
*   **Ambient Sounds / Presence Footsteps**: Suoni ambientali e dei passi immersivi.
*   **Snow! Real Magic!**: Neve più realistica e accumulabile.
*   **Soul Fired**: Il fuoco blu brucia blu anche sulle entità.
*   **Sound Physics Remastered**: Aggiunge riverbero ed eco dinamico in base all'ambiente.

## ⚙️ Librerie Tecniche
*Necessarie per far funzionare le altre mod.*

*   **Fabric API**, **Architectury API**, **Cloth Config API**, **JamLib**, **libIPN**, **malilib**, **YACL**, **OctoLib**, **Fabric Language Kotlin**, **Iceberg**, **Prism**, **Puzzles Lib**, **Union Lib**, **OOO Lib**, **MRU**, **Collective**, **Creative Core**, **Crystal Lib**, **Prometheus**, **Forge Config API Port**, **Fzzy Config**, **configurable**, **ukulib**, **WalksyLib**.

## 🔧 Fix Vari
*   **Crash Assistant**: Analizza e spiega le cause dei crash del gioco.
*   **MixinTrace / MixinTrace Reloaded**: Fornisce log più dettagliati per il debug.
*   **Shut Up GL Error**: Nasconde gli errori grafici OpenGL non critici.
*   **Debugify**: Corregge centinaia di bug del gioco vanilla.
*   **Packet Fixer**: Risolve problemi legati ai pacchetti di rete troppo grandi.
*   **Neruina**: Previene crash causati da entità o blocchi corrotti (ticking entity).
