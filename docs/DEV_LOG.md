# Hydro Tracker; Developer Logs

**NOTE:** All time is in ***UTC***!

---

## Developers Log

### 2026/10/05

* 16:00
    - Starting to plan out the dual-software program.

* 20:33
    - The architecture was finished (somewhat) and now the
      daemon create fragment is finished.
    - Will begin creating the textual interface for the
      control panel in the hydro daemon.

---

### 2025/10/06

* 07:00
    - A simple template for the daemons application
      interface was created.
    - Stepping away for sleep.

* 17:55
  - Continuing to create the daemon app.

* 06:25
  - The whole day was blown off after having a template
    for a switching menu feature.
  - Updated `.gitignore`, made `fragments/get_data.py` run
    in "headless" mode, and broke the menu switcher trying
    to make the settings menu.

---

### 2026/10/07

* 20:40
  - Finished the base template for the settings page.
  - Next, I need to make the save button save to the
    config file. Also, I want to have the config info
    that is already set preset into the fields.

---

### 2026/10/08

* 18:37
  - Finished having the settings save, as well as
    created a custom secure password cryptographic
    module.
  - Next, I need to have the existing values get
    filled in on the settings page.

* 20:33
  - Existing values get prefilled in the settings.
  - Daemon screen now displays the status and buttons
    to control it.
  - A log screen has been added to the menus.

### 2026/10/09

* 06:20
  - Got the daemon creator working, might need to
    make it call a seperate binary to obtain data.
  - Secure Password binary is only functional on
    this machine. Testing delayed.

* 15:20
  - Trying to figure out how to have the secure pass
    binary secret and unaccessible to anyone but the
    script.

---

### 2026/10/14

* 20:00
  - Trying to get the client to send and receive data from
    the server without causing a timeout.

---

### 2026/10/16

* 16:35
  - Fixed the connection transaction and can simply
    encrypt and decrypt with a custom hash and nonce.

---

### 2026/10/19

* 14:40
  - Finishing up the Secure Password module to allow a
    simple compilation and usage of the program.

---

### 2026/10/24

* 04:00
  - Verified and fixed the server. now the client needs to
    be rewritten for the Hydro Tracker.

---

### 2026/10/28

* 04:55
  - Commented on the server section of the secure password
    module.
  - I need to stress test the API to ensure invalid
    requests do not go through.
  - Also need to rewrite the client into its own section
    for the hydro tracker module.

---

## TO-DO
[!!!!!!] Rewrite the client module.
[!!!!!!] Requires a thorough stress test on the API
         responses.
