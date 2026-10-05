# Hydro Tracker; Dual-System Architecture

This is a dual-system program that obtains data from your
Hydro Ottawa dashboard and allows you to view it within 
a simple terminal interface! The two systems are these:

* **Hydro-Daemon:** Controls the Daemon to obtain the data.
* **Hydro-Usage:** Display the updated Hydro usage data.

---

## Hydro Daemon


Checks for config file and creates it.

Acts as the control panel for setting up the daemon for
obtaining and cleaning the hydro data for processing. It
can be called with or without arguments. The `--update`
flag just updates the data without launching the control
panel. Within the control panel, it is a TUI that allows
setting up the systemd for the daemon, checking its logs
and toggling automatic updates.

Creates a systemd that calls the daemons update function
on a set time.

---

## Hydro Usage

Reads the cleaned json data files so the data can be
displayed. It lets the user view each record of hydro
usage for each day in the current billing period. The
records can be updated within with a `u`pdate command
so the record can be up-to-date live.

Future versions will include a toggle a bar graph to
view that days `h`ourly hydro usage.

---

### Installation Model

An `install.sh` script is used to compile the code into
the required binaries and place them in the `/usr/bin/`
directory so the commands can be called directly.
