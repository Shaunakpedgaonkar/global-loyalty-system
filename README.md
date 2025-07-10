# 🌍 Global Loyalty Card System

A distributed, multi-region loyalty platform for a global café chain, supporting real-time, fault-tolerant transactions across **US, Ireland, and India**. Built to ensure **performance, consistency, and availability** for a globally mobile user base.

---

## 🚀 Features

- 🌐 **Multi-Region Deployment** using AWS Free Tier (EC2) in US, Ireland, and India
- 🔁 **MySQL Multi-Master Group Replication** for cross-region consistency and fault-tolerance
- 🔐 **JWT-based Flask APIs** with Dockerized deployment behind HTTPS domain-level security
- 📉 Real-time telemetry via **OpenTelemetry** + **Signoz**, with performance testing via **JMeter**
- 📱 UI frontend (mobile-first) acts as a contactless loyalty card for seamless user experience

---

## 📦 Tech Stack

**Backend:** Python Flask, MySQL Group Replication, Docker  
**DevOps:** AWS EC2, Route 53, ELB, OpenTelemetry, JMeter  
**Security:** JWT authentication, HTTPS with domain verification  
**Frontend:** HTML/CSS (simple UI), multi-region API integration  
**Monitoring:** Signoz dashboards powered by OpenTelemetry  
**Testing:** Automated JMeter CLI tests running continuously

---

## 🔧 Architecture Overview

- Regional routing via **Amazon Route 53** (latency-based)
- Each region uses a **Dockerized Flask API stack** with JWT auth
- All transactions go through **MySQL Multi-Master Replication** ensuring consistency across all servers
- Real-time health checks and failover logic in place (custom Flask failover fallback logic)
- latency managed through synchronous consensus replication; optimized for read-heavy traffic


---

## 🔐 Key Functionalities

- **User Registration / Login:** JWT issued on login, used for session control
- **Loyalty Card Management:** Add family members (up to 4), retrieve coins
- **Transaction API:** Add/redeem transactions, maintain global consistency
- **Cross-Region Redemption:** Earn points in one region, redeem globally
- **Failover Protection:** Automated fallback to backup DB region on node failure

---

## 📈 Performance

- ⚡ < 3s latency from request to response in most regions
- 🧪 10,000+ API hits simulated with **JMeter** per region
- 📊 Real-time metrics available at: [Signoz Dashboard](https://observe.pastav.com/)

---

## 🧪 How to Run (Local)

```bash
git clone https://github.com/shaunakpedgaonkar/global-loyalty-system.git
cd global-loyalty-system
docker-compose up --build
