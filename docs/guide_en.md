# Media Searcher – User Guide

A program that turns audio recordings into written text. It runs entirely on your computer and never sends recordings to the internet.
It is designed to be fully usable from the keyboard and with a screen reader (such as NVDA).

## Installing and starting

- Run the installer (`MediaSearcher-Setup-1.0.0.exe`, for example) and choose the setup language. The language you choose also becomes the program's language; you can change it later in Settings.
- The program installs into Program Files (Windows asks for administrator approval), and your data (settings, dictionaries, models) is stored in your account folder `%APPDATA%\MediaSearcher`. It is added to the Start menu as "Media Searcher" (always in English, whatever the program's language). You can also choose to add a desktop shortcut.
- When you install a newer version over an older one, your settings, dictionaries and models are kept.
- To remove the program: Windows Settings > Apps. The uninstaller asks whether to delete your data or keep it.
- You can also open any audio file with the program (right-click the file > Open with); transcription starts immediately.

## First run

The program needs an AI model, downloaded from the internet once; after that it works offline.
On first run, the program offers to open the Model Manager (Ctrl+D) with the model recommended for your computer already selected. Press "Start download" and wait for it to finish.

## Transcribing an audio file

1. Press `Ctrl+O` and choose the file, or `Ctrl+M` to transcribe every file in a folder.
2. Choose the right dictionary from the "Dictionary:" list next to the "Start Transcription" button (see Dictionaries).
3. Press "Start Transcription".
4. The processing window opens with focus on the progress line. Progress, the current step and the remaining time are announced automatically every 10%. Press `Ctrl+I` to hear them at any time, and `Esc` to cancel.
   - Arrow down for the file (and, in folder mode, "file 3 of 10"), then the position reached in the recording, the elapsed time and the number of sentences.
   - The "Text so far" box shows sentences as they are transcribed.
   - **Pause** stops after the sentence being transcribed, and **Resume** continues from the same place. Paused time is not counted in the report.
   - **Run in background** hides the window while transcription continues; progress shows in the status bar and window title. Press `Ctrl+I` to bring it back. When it finishes, the program's taskbar button flashes if you are in another program.
5. Sentences appear in the results list as they are transcribed.
6. When finished, a sound plays and the quality report opens. Close it with `Esc`; focus moves to the first result line.
7. Every report is kept: open "Activity History" with `Ctrl+H`, choose any transcription, and press `Enter` (or "View report") to read its full report again. The history keeps the last 100 transcriptions.

## Reviewing and correcting results

- Move between lines with the arrow keys. Each line reads: the text, then the time, then the review column.
- If the model was unsure of a word, the review column says "uncertain words: ...", and the line is shown in red.
- `Enter`: play the sentence and stop at its end (change this in View > Play sentence only).
- `F3`: pause and resume. `F4`: stop playback. `Alt+Right` and `Alt+Left`: forward and back 5 seconds.
- `F2`: edit the line. In the edit window: `F5` to listen, `Ctrl+Enter` to save, `Ctrl+Shift+S` to split the sentence at the cursor, `Esc` to cancel.
- `Ctrl+J`: merge the selected line with the next sentence.
- `Ctrl+F`: search within the results.
- `Ctrl+S`: save the results as SRT, TXT, VTT, JSON or Word. If you have unsaved edits, the program asks before closing.

## Searching all files

Press `Ctrl+Tab` to go to the "Global Search" tab, choose the folder, type the word and press `Enter`.
The number of results is read with the list name, and `Enter` on a result plays the audio from that moment (if the audio file has the same name as the subtitle file and is in the same folder).

## If transcription is interrupted

Progress is saved every 5 seconds. If you cancel, the program closes, or the power goes out, open the same file again and you will be offered to "Continue" from where it stopped, or "Start over".
If an unfinished transcription exists when you open the program, it offers to continue it.

## Dictionaries

You can create a dictionary for each field (Quran, lectures, meetings...) and choose it before transcribing from the "Dictionary:" list next to the "Start Transcription" button.
This keeps one field's corrections from spoiling another: a correction that is right in one kind of recording can be wrong in another.

Press `Ctrl+K` to open "Manage dictionaries". Each dictionary has two tabs:

- **Corrections**: "wrong word → correct word", applied to the text after transcription. `Enter` adds, `Delete` removes.
- **Terms and names**: correct names and terms expected in the recordings, with no need to know the mistakes. They are given to the model as hints, so it writes them correctly from the start.

An example from testing: the model wrote the computer name "ENIAC" in four different wrong ways across five sentences; after adding it as a term, all five were correct.

`Ctrl+Shift+K`: apply the whole dictionary to the current results (useful after adding words, or on an opened subtitle file).

**Import and export**: export any dictionary to a file to share it or move it to another computer, and import dictionaries from:

- A file exported by the program (JSON).
- A CSV file (from Excel): two columns (wrong, correct) for corrections, or one column for terms.
- A text file: one term per line, or a correction written as "wrong → correct" (or with `=`).

## Learning from your corrections

When you correct a line with `F2`, the program compares the old and new text and finds the word you corrected, then asks:

- **Learn and apply to the rest**: also corrects it everywhere in the current results.
- **Learn only**: remembers it for next time.
- **Ignore**: if the correction was right for that sentence only.

What the program learns is saved in the selected dictionary, corrected automatically in future transcriptions, and given to the model as a hint so it writes the word correctly from the start.
Each correction is also kept as a training example (the sentence audio with its correct text). You can export them from Settings > Smart Correction > Export training data, to fine-tune the model on a computer with a GPU.

In Settings, learning can be set to: ask each time (default), automatic (after the same correction twice), or off.

## Important settings (Ctrl+P)

- **Skip silence and music**: on by default. Prevents the model from writing made-up text during silence and noise, speeds up long files, and is tuned not to cut off long drawn-out endings such as recitation.
- **Source audio language**: the language of the recording, or "Auto-detect".
- **Model status**: shows whether the selected model is on your computer or will be downloaded.
- **Theme**: light or dark. The main window changes immediately; other windows after restarting the program.

## Keyboard shortcuts

Press `Shift+F1` for the full list of shortcuts.

## If something goes wrong

Errors are recorded in detail in `logs/app.log` inside the program's data folder (the same folder that holds the settings file).
