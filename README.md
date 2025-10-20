# AWS Secure Journal API Deployment

A simple journal application deployed on AWS as part of the **Learn to Cloud (L2C) Guide - [Cloud Deployment](https://learntocloud.guide/phase3/deploy-api)**.

This repository contains the **FastAPI backend** for storing and managing journal entries in a **PostgreSQL database** hosted on a private EC2 instance.

The deployment follows AWS best practices with a secure VPC, public/private subnets, IAM roles, SSM access, and automated database backups.

Wrote a short article walking through my setup, security design, challenges, and what I learned along the way.....check it out [here](https://www.linkedin.com/pulse/deploying-secure-journal-api-aws-what-i-learned-govindagari-rcvsc)

---

## Architecture Diagram

## ![Architecture Diagram](Architecture.png)

## 1. Infrastructure Setup (AWS Console)

### VPC and Networking

- Create a new **VPC** (Note: Plan your CIDR blocks accordingly)
- Add:
  - **Public Subnet** (for API EC2)
  - **Private Subnet** (for DB EC2)
- Configure **Route Tables**:
- Create and attach an **Internet Gateway**.
- Create a **NAT Gateway** in the public subnet for private instance outbound access.
- Allocate and associate an **Elastic IP** (used by NAT and API EC2).

### Security Groups

- **journal-api-sg**: Allow inbound HTTP (80) from anywhere; SSH (22) from your IP only and outbound to anywhere.
- **journal-db-sg**: Allow inbound PostgreSQL (5432) from `journal-api-sg` only; outbound to anywhere.

---

## 2. Deploy and Configure the API Server

### Launch EC2 (Public Subnet)

- Launch Ubuntu instance in the public subnet.
- Assign the **Elastic IP**.
- Attach security group: `journal-api-sg`.
- SSH into instance and install dependencies:

```bash
sudo apt update -y
sudo apt install -y python3 python3-venv git nginx
```

### Clone and Run Application

```bash
git clone https://github.com/<your-username>/aws-secure-journal-api.git
cd aws-secure-journal-api/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure Environment

**Create a .env file:**

```bash
sudo nano .env
```

Add:

```bash
POSTGRES_USER=journal_user
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=career_journal
DATABASE_URL=postgresql://journal_user:yourpassword@<private-db-ip>:5432/career_journal
```

**Test Locally:**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Visit: `http://Your-Elastic-IP/docs`

### Nginx Reverse Proxy + Systemd

**Configure Nginx:**

```
sudo nano /etc/nginx/conf.d/fastapi.conf
```

Add:

```
server {
listen 80;
server_name <Elastic-IP>;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

}
```

Test and reload Nginx:

```
sudo nginx -t
sudo systemctl reload nginx
```

**Create systemd service:**

```
sudo nano /etc/systemd/system/fastapi.service
```

Add:

```
[Unit]
Description=FastAPI Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/aws-secure-journal-api/api
Environment="PATH=/home/ubuntu/aws-secure-journal-api/api/venv/bin"
ExecStart=/home/ubuntu/aws-secure-journal-api/api/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl start fastapi
sudo systemctl status fastapi
```

## 3. Deploy and Configure the Database Server

### Launch EC2 (Private Subnet)

- Launch Ubuntu instance in private subnet (no public IP).
- Attach security group: `journal-db-sg`.
- Attach IAM role: `journal-postgres-role` with:
  - AmazonSSMManagedInstanceCore
  - S3 access policy for backups.

Connect using Session Manager.

Install PostgreSQL:

```bash
sudo apt update -y
sudo apt install -y postgresql postgresql-contrib
```

Create DB and user:

```bash
sudo -u postgres psql
CREATE USER journal_user WITH PASSWORD 'yourpassword';
CREATE DATABASE career_journal OWNER journal_user;
ALTER ROLE journal_user WITH LOGIN;
\q
```

Edit configuration files:

```bash
sudo nano /etc/postgresql/*/main/postgresql.conf
# Listen on all interfaces
listen_addresses = '*'

sudo nano /etc/postgresql/*/main/pg_hba.conf
# Allow connections from API subnet
host all journal_user <API_SUBNET_CIDR> scram-sha-256
```

Restart PostgreSQL:

```
sudo systemctl restart postgresql
```

Test Connection (from API EC2)

```
psql -h <private-db-ip> -U journal_user -d career_journal
```

Create table schema:

```sql
CREATE TABLE IF NOT EXISTS entries (
id VARCHAR PRIMARY KEY,
data JSONB NOT NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at);
CREATE INDEX IF NOT EXISTS idx_entries_data_gin ON entries USING GIN (data);
```

## 4. Database Backup Automation (Cron + S3)

**Create backup script:**

```bash
sudo nano /usr/local/bin/pg_backup.sh
```

Add:

```
#!/bin/bash
BACKUP*DIR="/var/backups/postgres"
DATE=$(date +%Y-%m-%d*%H-%M)
DB_NAME="career_journal"
USER="journal_user"
BUCKET="journal-db-backups"

sudo -u postgres pg_dump -Fc -d $DB_NAME > "$BACKUP_DIR/${DB_NAME}*$DATE.dump"
gzip "$BACKUP_DIR/${DB_NAME}*$DATE.dump"
aws s3 cp "$BACKUP_DIR/${DB_NAME}*$DATE.dump.gz" s3://$BUCKET/
```

Make executable:

```
sudo chmod +x /usr/local/bin/pg_backup.sh
```

Test:

```
sudo /usr/local/bin/pg_backup.sh
aws s3 ls s3://journal-db-backups/
```

Add daily cron job:

```
sudo crontab -e
0 2 \* \* \* /usr/local/bin/pg_backup.sh >> /var/log/pg_backup.log 2>&1

```

## Architecture Summary

| Component  | Network               | Description                                            |
| ---------- | --------------------- | ------------------------------------------------------ |
| API Server | Public Subnet         | FastAPI + Nginx + systemd, Elastic IP                  |
| DB Server  | Private Subnet        | PostgreSQL, private-only access                        |
| Backup     | S3 Bucket             | Stores automated database backups                      |
| IAM Role   | journal-postgres-role | Allows S3 uploads and SSM access for secure management |

---

## Future Scope

There are a few things I plan to improve later to make this closer to a production-grade setup:

- **Enable HTTPS with Managed Certificates:** Use AWS ACM (or Let’s Encrypt) to run the app over HTTPS instead of plain HTTP.
- **Automated Updates:** Set up simple cron jobs to keep PostgreSQL and the OS up to date automatically.
- **Application Load Balancer (ALB):** Eventually, replace the Elastic IP with an ALB for better scalability and fault tolerance. That’ll be part of my next [project](https://github.com/shiva0824/Jobs).
