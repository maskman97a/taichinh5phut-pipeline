@echo off
REM ============================================================
REM Download 10 Kevin MacLeod tracks (CC-BY 4.0) tu Incompetech
REM Cách dùng: Double-click file này, hoặc trong CMD:
REM   cd /D D:\TungPT\youtube_new\github_repo\audio
REM   download_bgm.bat
REM ============================================================

cd /D %~dp0

echo Downloading 10 royalty-free tracks from Incompetech...
echo (Kevin MacLeod, CC-BY 4.0 - phai ghi credit)
echo.

REM 1. Backed Vibes Clean - Hip-hop, upbeat, tech-feeling (8.8MB)
curl -L -o bgm_01_backed_vibes.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Backed%%20Vibes%%20Clean.mp3"

REM 2. Inspired - Cinematic inspirational (8.7MB)
curl -L -o bgm_02_inspired.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Inspired.mp3"

REM 3. Lobby Time - Corporate calm (5.9MB)
curl -L -o bgm_03_lobby_time.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Lobby%%20Time.mp3"

REM 4. Carefree - Light positive (6.3MB)
curl -L -o bgm_04_carefree.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Carefree.mp3"

REM 5. Local Forecast Elevator - Lofi lounge (7.2MB)
curl -L -o bgm_05_local_forecast.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Local%%20Forecast%%20-%%20Elevator.mp3"

REM 6. Sneaky Snitch - Sneaky tech (5.2MB)
curl -L -o bgm_06_sneaky_snitch.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Sneaky%%20Snitch.mp3"

REM 7. Investigations - Mystery tech (3.6MB)
curl -L -o bgm_07_investigations.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Investigations.mp3"

REM 8. Werq - Upbeat funk (5MB)
curl -L -o bgm_08_werq.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Werq.mp3"

REM 9. Funky Chunk - Funky upbeat (7.3MB)
curl -L -o bgm_09_funky_chunk.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Funky%%20Chunk.mp3"

REM 10. Aces High - Inspirational cinematic (7.4MB)
curl -L -o bgm_10_aces_high.mp3 "https://incompetech.com/music/royalty-free/mp3-royaltyfree/Aces%%20High.mp3"

echo.
echo === DELETE 5 OLD PIXABAY TRACKS ===
del /q bgm_cinematic_ambient_03.mp3 2>nul
del /q bgm_corporate_02.mp3 2>nul
del /q bgm_inspiring_background_05.mp3 2>nul
del /q bgm_lofi_01.mp3 2>nul
del /q bgm_motivational_04.mp3 2>nul

echo.
echo === FINAL CHECK ===
dir *.mp3

echo.
echo ============================================================
echo Done! 10 BGM tracks Kevin MacLeod CC-BY 4.0 ready.
echo.
echo IMPORTANT: phai them credit trong YouTube description:
echo "Music: Kevin MacLeod (incompetech.com)"
echo "Licensed under Creative Commons: By Attribution 4.0"
echo "https://creativecommons.org/licenses/by/4.0/"
echo ============================================================
pause
