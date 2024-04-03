#!/bin/bash

# Arrête le script si une commande échoue
set -e

# Fonction pour détecter l'OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "Linux";;
        Darwin*)    echo "MacOS";;
        CYGWIN*|MINGW32*|MSYS*|MINGW*) echo "Windows";;
        *)          echo "unknown"
    esac
}

OS=$(detect_os)
echo "Detected OS: $OS"

# Définir le chemin de base
BASE_PATH=$(pwd)

# Build poker-eval
echo "Building poker-eval..."
cd "${BASE_PATH}/fpdb-3/pypoker-eval/poker-eval"
mkdir -p build
cd build
if [[ "$OS" == "Windows" ]]; then
    cmake .. -G "Visual Studio 17 2022"
    cmake --build .
elif [[ "$OS" == "Linux" || "$OS" == "MacOS" ]]; then
    cmake ..
    make
fi
# Retour au chemin de base pour éviter les confusions
cd "${BASE_PATH}"

# Build pypoker-eval
echo "Building pypoker-eval..."
cd "${BASE_PATH}/fpdb-3/pypoker-eval"
mkdir -p build
cd build
if [[ "$OS" == "Windows" ]]; then
    cmake .. -G "Visual Studio 17 2022"
    cmake --build .
elif [[ "$OS" == "Linux" || "$OS" == "MacOS" ]]; then
    cmake ..
    make
fi
# Retour au chemin de base à nouveau
cd "${BASE_PATH}"

# Build fpdb-3
echo "Building fpdb-3..."
cd "${BASE_PATH}/fpdb-3"
# Commandes spécifiques à chaque OS pour construire fpdb-3 si nécessaire

if [[ "$OS" == "Windows" ]]; then
    echo "Copying and renaming pypokereval.dll to _pokereval_3_11.pyd for Windows..."
    cp "${BASE_PATH}/fpdb-3/pypoker-eval/build/Debug/pypokereval.dll" "${BASE_PATH}/fpdb-3/_pokereval_3_11.pyd"
    echo "Copying pokereval.py to fpdb-3..."
    cp "${BASE_PATH}/fpdb-3/pypoker-eval/pokereval.py" "${BASE_PATH}/fpdb-3/"


    # Chemin de base où se trouvent tes fichiers Python

    BASE_PATH2="$(echo ${BASE_PATH:1:1} | tr '[:lower:]' '[:upper:]'):${BASE_PATH:2}"
    BASE_PATH2="${BASE_PATH2}/fpdb-3"

    echo "Adjusted BASE_PATH2 for Windows: $BASE_PATH2"

    # Nom du script principal pour lequel générer l'exécutable
    MAIN_SCRIPT="fpdb.pyw"
    SECOND_SCRIPT="HUD_main.pyw"

    # Options de base PyInstaller
    PYINSTALLER_OPTIONS="--noconfirm --onedir --windowed"

    # Liste de tous les fichiers et dossiers à ajouter
    FILES=(
        "Anonymise.py"
        "api.py"
        "app.py"
        "Archive.py"
        "Aux_Base.py"
        "Aux_Classic_Hud.py"
        "Aux_Hud.py"
        "base_model.py"
        "BetfairToFpdb.py"
        "BetOnlineToFpdb.py"
        "BovadaSummary.py"
        "BovadaToFpdb.py"
        "bug-1823.py"
        "CakeToFpdb.py"
        "Card.py"
        "Cardold.py"
        "card_path.py"
        "Charset.py"
        "Configuration.py"
        "contributors.txt"
        "Database.py"
        "Databaseold.py"
        "db_sqlite3.md"
        "decimal_wrapper.py"
        "Deck.py"
        "dependencies.txt"
        "DerivedStats.py"
        "DerivedStats_old.py"
        "DetectInstalledSites.py"
        "Exceptions.py"
        "files.qrc"
        "files_rc.py"
        "Filters.py"
        "fpdb.pyw"
        "fpdb.toml"
        "fpdb_prerun.py"
        "GGPokerToFpdb.py"
        "GuiAutoImport.py"
        "GuiBulkImport.py"
        "GuiDatabase.py"
        "GuiGraphViewer.py"
        "GuiHandViewer.py"
        "GuiLogView.py"
        "GuiOddsCalc.py"
        "GuiPositionalStats.py"
        "GuiPrefs.py"
        "GuiReplayer.py"
        "GuiRingPlayerStats.py"
        "GuiSessionViewer.py"
        "GuiStove.py"
        "GuiTourneyGraphViewer.py"
        "GuiTourneyImport.py"
        "GuiTourneyPlayerStats.py"
        "GuiTourneyViewer.py"
        "Hand.py"
        "HandHistory.py"
        "HandHistoryConverter.py"
        "Hello.py"
        "Hud.py"
        "HUD_config.test.xml"
        "HUD_config.xml"
        "HUD_config.xml.example"
        "HUD_config.xml.exemple"
        "HUD_main.pyw"
        "HUD_run_me.py"
        "IdentifySite.py"
        "Importer-old.py"
        "Importer.py"
        "ImporterLight.py"
        "interlocks.py"
        "iPokerSummary.py"
        "iPokerToFpdb.py"
        "KingsClubToFpdb.py"
        "L10n.py"
        "LICENSE"
        "linux_table_detect.py"
        "logging.conf"
        "Makefile"
        "MergeStructures.py"
        "MergeSummary.py"
        "MergeToFpdb.py"
        "montecarlo.py"
        "Mucked.py"
        "OddsCalc.py"
        "OddsCalcnew.py"
        "OddsCalcNew2.py"
        "OddsCalcPQL.py"
        "Options.py"
        "OSXTables.py"
        "P5sResultsParser.py"
        "PacificPokerSummary.py"
        "PacificPokerToFpdb.py"
        "PartyPokerToFpdb.py"
        "Pokenum_api_call.py"
        "pokenum_example.py"
        "pokereval.py"
        "PokerStarsStructures.py"
        "PokerStarsSummary.py"
        "PokerStarsToFpdb.py"
        "PokerTrackerSummary.py"
        "PokerTrackerToFpdb.py"
        "Popup.py"
        "ppt.py"
        "ps.ico"
        "RazzStartHandGenerator.py"
        "run_fpdb.py"
        "RushNotesAux.py"
        "RushNotesMerge.py"
        "ScriptAddStatToRegression.py"
        "ScriptFetchMergeResults.py"
        "ScriptFetchWinamaxResults.py"
        "ScriptGenerateWikiPage.py"
        "SealsWithClubsToFpdb.py"
        "settings.json"
        "setup.py"
        "sim.py"
        "sim2.py"
        "simulation.py"
        "SitenameSummary.py"
        "SplitHandHistory.py"
        "SQL.py"
        "sql_request.py"
        "start_fpdb_web.py"
        "Stats.py"
        "Stove.py"
        "Summaries.py"
        "TableWindow.py"
        "TestDetectInstalledSites.py"
        "TestHandsPlayers.py"
        "testodd.py"
        "TournamentTracker.py"
        "TourneySummary.py"
        "TreeViewTooltips.py"
        "UnibetToFpdb.py"
        "UnibetToFpdb_old.py"
        "upd_indexes.sql"
        "wina.ico"
        "WinamaxSummary.py"
        "WinamaxToFpdb.py"
        "windows_make_bats.py"
        "WinningSummary.py"
        "WinningToFpdb.py"
        "WinTables.py"
        "win_table_detect.py"
        "xlib_tester.py"
        "XTables.py"
        "_pokereval_3_11.pyd"
    )

    FOLDERS=(
        "gfx;gfx/"
        "icons;icons/"
        "fonts;fonts/"
        "locale;locale/"
        "ppt;ppt/"
        "static;static/"
        "templates;templates/"
        "utils;utils/"
    )        

    # Fonction pour générer la commande PyInstaller avec --add-data
    generate_pyinstaller_command() {
        local script_path="$1"
        local command="pyinstaller $PYINSTALLER_OPTIONS"

        # Traite les fichiers
        for file in "${FILES[@]}"; do
            if [[ "$OS" == "Windows" ]]; then
                command+=" --add-data \"$BASE_PATH2/$file;.\""
            else
                command+=" --add-data \"$BASE_PATH2/$file:.\""
            fi
        done

        # Traite les dossiers
        for folder in "${FOLDERS[@]}"; do
            # Enlève le préfixe 'nom_dossier;' pour le chemin source et le suffixe '/' pour le dest_path
            local src_folder="${folder%%;*}"
            local dest_folder="${folder##*;}"
            if [[ "$OS" == "Windows" ]]; then
                command+=" --add-data \"$BASE_PATH2/$src_folder;$dest_folder\""
            else
                command+=" --add-data \"$BASE_PATH2/$src_folder:$dest_folder\""
            fi
        done

        command+=" \"$BASE_PATH2/$script_path\""

        echo "$command"
    }




    # Générer et exécuter la commande pour le script principal
    command=$(generate_pyinstaller_command $MAIN_SCRIPT)
    echo "Exécution : $command"
    eval $command

    # Générer et exécuter la commande pour le second script, si nécessaire
    command=$(generate_pyinstaller_command $SECOND_SCRIPT)
    echo "Exécution : $command"
    eval $command

    echo "Build terminé avec succès."

    
elif [[ "$OS" == "MacOS" ]]; then
    echo "Copying and renaming pypokereval.so to _pokereval_3_11.so for MacOs..."
    cp "${BASE_PATH}/fpdb-3/pypoker-eval/build/pypokereval.so" "${BASE_PATH}/fpdb-3/_pokereval_3_11.so"
    echo "Copying pokereval.py to fpdb-3..."
    cp "${BASE_PATH}/fpdb-3/pypoker-eval/pokereval.py" "${BASE_PATH}/fpdb-3/"
elif [[ "$OS" == "Linux" ]]; then
    echo "Copying and renaming pypokereval.so to _pokereval_3_11.so for Linux..."
    cp "${BASE_PATH}/fpdb-3/pypoker-eval/build/pypokereval.so" "${BASE_PATH}/fpdb-3/_pokereval_3_11.so"
    echo "Copying pokereval.py to fpdb-3..."
    cp "${BASE_PATH}/fpdb-3/pypoker-eval/pokereval.py" "${BASE_PATH}/fpdb-3/"


    # Chemin de base où se trouvent tes fichiers Python

    #BASE_PATH2="$(echo ${BASE_PATH:1:1} | tr '[:lower:]' '[:upper:]'):${BASE_PATH:2}"
    BASE_PATH2="${BASE_PATH}/fpdb-3"

    echo "Adjusted BASE_PATH2 for Windows: $BASE_PATH2"

    # Nom du script principal pour lequel générer l'exécutable
    MAIN_SCRIPT="fpdb.pyw"
    SECOND_SCRIPT="HUD_main.pyw"
    HUD_MAIN_PATH="${BASE_PATH2}"

    PYINSTALLER_OPTIONS="--noconfirm --onedir --windowed"

    # Spécifiez ici le chemin vers HUD_main.pyw pour l'extraire explicitement
    EXTRA_DATA="${HUD_MAIN_PATH}:."

    # Liste de tous les fichiers et dossiers à ajouter
    FILES=(
        "Anonymise.py"
        "api.py"
        "app.py"
        "Archive.py"
        "Aux_Base.py"
        "Aux_Classic_Hud.py"
        "Aux_Hud.py"
        "base_model.py"
        "BetfairToFpdb.py"
        "BetOnlineToFpdb.py"
        "BovadaSummary.py"
        "BovadaToFpdb.py"
        "bug-1823.py"
        "CakeToFpdb.py"
        "Card.py"
        "Cardold.py"
        "card_path.py"
        "Charset.py"
        "Configuration.py"
        "contributors.txt"
        "Database.py"
        "Databaseold.py"
        "db_sqlite3.md"
        "decimal_wrapper.py"
        "Deck.py"
        "dependencies.txt"
        "DerivedStats.py"
        "DerivedStats_old.py"
        "DetectInstalledSites.py"
        "Exceptions.py"
        "files.qrc"
        "files_rc.py"
        "Filters.py"
        "fpdb.pyw"
        "fpdb.toml"
        "fpdb_prerun.py"
        "GGPokerToFpdb.py"
        "GuiAutoImport.py"
        "GuiBulkImport.py"
        "GuiDatabase.py"
        "GuiGraphViewer.py"
        "GuiHandViewer.py"
        "GuiLogView.py"
        "GuiOddsCalc.py"
        "GuiPositionalStats.py"
        "GuiPrefs.py"
        "GuiReplayer.py"
        "GuiRingPlayerStats.py"
        "GuiSessionViewer.py"
        "GuiStove.py"
        "GuiTourneyGraphViewer.py"
        "GuiTourneyImport.py"
        "GuiTourneyPlayerStats.py"
        "GuiTourneyViewer.py"
        "Hand.py"
        "HandHistory.py"
        "HandHistoryConverter.py"
        "Hello.py"
        "Hud.py"
        "HUD_config.test.xml"
        "HUD_config.xml"
        "HUD_config.xml.example"
        "HUD_config.xml.exemple"
        "HUD_main.pyw"
        "HUD_run_me.py"
        "IdentifySite.py"
        "Importer-old.py"
        "Importer.py"
        "ImporterLight.py"
        "interlocks.py"
        "iPokerSummary.py"
        "iPokerToFpdb.py"
        "KingsClubToFpdb.py"
        "L10n.py"
        "LICENSE"
        "linux_table_detect.py"
        "logging.conf"
        "Makefile"
        "MergeStructures.py"
        "MergeSummary.py"
        "MergeToFpdb.py"
        "montecarlo.py"
        "Mucked.py"
        "OddsCalc.py"
        "OddsCalcnew.py"
        "OddsCalcNew2.py"
        "OddsCalcPQL.py"
        "Options.py"
        "OSXTables.py"
        "P5sResultsParser.py"
        "PacificPokerSummary.py"
        "PacificPokerToFpdb.py"
        "PartyPokerToFpdb.py"
        "Pokenum_api_call.py"
        "pokenum_example.py"
        "pokereval.py"
        "PokerStarsStructures.py"
        "PokerStarsSummary.py"
        "PokerStarsToFpdb.py"
        "PokerTrackerSummary.py"
        "PokerTrackerToFpdb.py"
        "Popup.py"
        "ppt.py"
        "ps.ico"
        "RazzStartHandGenerator.py"
        "run_fpdb.py"
        "RushNotesAux.py"
        "RushNotesMerge.py"
        "ScriptAddStatToRegression.py"
        "ScriptFetchMergeResults.py"
        "ScriptFetchWinamaxResults.py"
        "ScriptGenerateWikiPage.py"
        "SealsWithClubsToFpdb.py"
        "settings.json"
        "setup.py"
        "sim.py"
        "sim2.py"
        "simulation.py"
        "SitenameSummary.py"
        "SplitHandHistory.py"
        "SQL.py"
        "sql_request.py"
        "start_fpdb_web.py"
        "Stats.py"
        "Stove.py"
        "Summaries.py"
        "TableWindow.py"
        "TestDetectInstalledSites.py"
        "TestHandsPlayers.py"
        "testodd.py"
        "TournamentTracker.py"
        "TourneySummary.py"
        "TreeViewTooltips.py"
        "UnibetToFpdb.py"
        "UnibetToFpdb_old.py"
        "upd_indexes.sql"
        "wina.ico"
        "WinamaxSummary.py"
        "WinamaxToFpdb.py"
        "windows_make_bats.py"
        "WinningSummary.py"
        "WinningToFpdb.py"
        "WinTables.py"
        "win_table_detect.py"
        "xlib_tester.py"
        "XTables.py"
        "_pokereval_3_11.so"
    )

    FOLDERS=(
        "gfx;gfx/"
        "icons;icons/"
        "fonts;fonts/"
        "locale;locale/"
        "ppt;ppt/"
        "static;static/"
        "templates;templates/"
        "utils;utils/"
    )        

    # Fonction pour générer la commande PyInstaller avec --add-data
    generate_pyinstaller_command() {
        local script_path="$1"
        local command="pyinstaller $PYINSTALLER_OPTIONS"

        # Traite les fichiers
        for file in "${FILES[@]}"; do
            if [[ "$OS" == "Windows" ]]; then
                command+=" --add-data \"$BASE_PATH2/$file;.\""
            else
                command+=" --add-data \"$BASE_PATH2/$file:.\""
            fi
        done

        # Traite les dossiers
        for folder in "${FOLDERS[@]}"; do
            # Enlève le préfixe 'nom_dossier;' pour le chemin source et le suffixe '/' pour le dest_path
            local src_folder="${folder%%;*}"
            local dest_folder="${folder##*;}"
            if [[ "$OS" == "Windows" ]]; then
                command+=" --add-data \"$BASE_PATH2/$src_folder;$dest_folder\""
            else
                command+=" --add-data \"$BASE_PATH2/$src_folder:$dest_folder\""
            fi
        done

        command+=" \"$BASE_PATH2/$script_path\""

        echo "$command"
    }




    # Générer et exécuter la commande pour le script principal
    command=$(generate_pyinstaller_command $MAIN_SCRIPT)
    echo "Exécution : $command"
    eval $command

    # Générer et exécuter la commande pour le second script, si nécessaire
    command=$(generate_pyinstaller_command $SECOND_SCRIPT)
    echo "Exécution : $command"
    eval $command

    echo "Build terminé avec succès."

fi

echo "All projects built successfully."
