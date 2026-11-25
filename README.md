# Odoo 18 Equipment Rental

An Odoo 18 development project for managing equipment rentals. The custom
`equipment_rental` module provides customer and equipment tracking, inclusive
rental-duration and total-cost calculations, multi-company currency support,
input validation, and a controlled draft-to-return/cancellation workflow.

## Run with Docker (recommended)

Requirements: Docker and Docker Compose.

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f odoo
```

Open [http://localhost:8069](http://localhost:8069), create a database, and use
`admin` as the master password. In Apps, update the app list and install
**Equipment Rental**.

Credential sources:

| Purpose | Configuration source | Default |
| --- | --- | --- |
| PostgreSQL container user, password, and maintenance database | `.env` (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) | `odoo`, `odoo`, `postgres` |
| Odoo connection to PostgreSQL | `odoo.conf` (`db_user`, `db_password`) | `odoo`, `odoo` |
| Odoo database-manager master password | `odoo.conf` (`admin_passwd`) | `admin` |

The PostgreSQL username and password in `.env` and `odoo.conf` must match.
The database administrator login used after database creation is chosen in the
browser and is separate from these credentials. `.env` also controls the host
web port through `ODOO_PORT` (default: `8069`).

Useful commands:

```bash
docker compose down              # Stop the project and keep its data
docker compose up -d             # Start it again
docker compose down -v           # Delete containers and all project data
```

For detailed Docker configuration and troubleshooting, see
[doc/docker/DOCKER_GUIDE.md](doc/docker/DOCKER_GUIDE.md).

## Run manually

Requirements: Python 3.10+, PostgreSQL, and the system libraries required by
Odoo. On Ubuntu/Debian, install the main dependencies:

```bash
sudo apt update
sudo apt install python3-venv python3-dev build-essential postgresql \
  libpq-dev libxml2-dev libxslt1-dev libldap2-dev libsasl2-dev \
  libjpeg-dev zlib1g-dev
```

Create a PostgreSQL user using the `db_user` and `db_password` values from
`odoo.conf` (both default to `odoo`), then install the Python dependencies.
The `.env` file is only used by Docker Compose and is not used for a manual run.

```bash
sudo -u postgres createuser --createdb --pwprompt odoo
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
mkdir -p .odoo-data
```

Start Odoo with local paths and PostgreSQL:

```bash
python odoo-bin -c odoo.conf \
  --db_host=localhost \
  --addons-path="$PWD/custom_addons,$PWD/addons,$PWD/odoo/addons" \
  --data-dir="$PWD/.odoo-data"
```

Open [http://localhost:8069](http://localhost:8069), create a database, and
install **Equipment Rental** from Apps.
