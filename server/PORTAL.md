# SQLite driver portal

The portal is part of the existing React client at `/portal`. It uses the same
FastAPI bridge on port `8000` and stores its data in `server/veritas.sqlite3`.
Starting `veritasbridge.py` creates the portal tables automatically.

## First administrator

1. Start the system and create an account at `/portal/signup`.
2. From the repository root, promote that account:

   ```bash
   python server/manage_portal.py you@example.com
   ```

3. Sign out and back in. The account will then have portal administration access.

New accounts are drivers by default. Passwords are stored as PBKDF2 hashes, and
the database stores only a hash of each session token.

## Portal capabilities

- Drivers can register vehicles, track ownership review, see confirmed violations
  associated with their verified plates, submit disputes, and update their profile.
- Administrators can verify/reject vehicle applications, review unassigned
  violations and disputes, and configure informational penalty amounts.
- Email verification, email password resets, and payment processing are not
  configured. The portal explains these limits instead of simulating those services.

Only approved Leanbot records whose plate matches an active, verified portal
vehicle are shown to that vehicle's owner.
