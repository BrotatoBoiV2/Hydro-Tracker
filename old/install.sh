# Install the secuepass binary first
nuitka --standalone --output-dir=build password_client.py --onefile -o secure_pass
mkdir lib
mv build/secure_pass lib/

nuitka --standalone --output-dir=build main.py --onefile -o hydro_tracker
mv build/hydro_tracker .
