# AWS Journal API Deployment

This project is part of the **Learn to Cloud (L2C) Guide - [Cloud Deployment](https://learntocloud.guide/phase3/deploy-api)**.

The goal was to get a small **FastAPI** app running on AWS, connected to a **PostgreSQL** database, and make sure everything runs securely in the cloud.

I wanted this to feel close to a real production setup but still simple enough to understand and manage on my own. I’ll be writing a more detailed post about the design, screenshots of API testing, issues I ran into, and lessons learned soon on **[LinkedIn](#)** (link coming later).

---

## Project Overview

This setup uses a basic two-tier design:

- **Application Layer (Public Subnet):** Runs the FastAPI app behind Nginx.
- **Database Layer (Private Subnet):** Runs PostgreSQL on a private EC2 instance that only the app server can reach.

---

## Deployment Summary

### 1. Network Setup

- Started by creating a VPC using Class C network design (192.168.0.0/24) range and divided it into four subnets.
- One subnet is public (for the FastAPI server) and one is private (for PostgreSQL). The remaining two are reserved for future use.
- Attached an Internet Gateway for public access and a NAT Gateway for secure outbound traffic from the private subnet.
- Then configured route tables and assigned an Elastic IP to the public instance.

This part was the trickiest because small mistakes in subnet or route settings can break connectivity. Once it worked, everything else got smoother.

---

### 2. API Server (Public Subnet)

The API server runs on an Ubuntu EC2 instance.

- Installed **Nginx** to forward web traffic from port 80 to the FastAPI app running on port 8000.
- The app runs with **uvicorn** and is managed by **systemd** so it starts automatically on reboot.
- Environment variables (like DB credentials) are stored in a `.env` file, and I tested all endpoints using Swagger UI (`/docs`).
  Once everything worked, hardened the firewall rules to allow only HTTP and internal DB connections.

---

### 3. Database Server (Private Subnet)

The database runs on another EC2 instance that has no public IP.

- It hosts a **PostgreSQL** database named `career_journal` with a dedicated user `journal_user`.
- Modified `postgresql.conf` and `pg_hba.conf` to accept only connections from the app server’s private IP.
  After that, the app could talk to the DB internally — no need for public access, which keeps things safer.

---

## Security and Access

The private PostgreSQL server is managed through **AWS Systems Manager (SSM)**.
That means I don’t need SSH keys or a public IP to connect — I can just use SSM Session Manager from the AWS console for secure shell access.

The DB instance also has an IAM role with the **AmazonSSMManagedInstanceCore** policy.
It can reach the internet safely through the NAT Gateway whenever it needs to install updates or send backups to S3.

This setup keeps the instance locked down but still manageable and up-to-date.

---

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
