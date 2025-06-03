# **Serverless Analytical Web App with AWS CDK**

## **Overview**

This project demonstrates the deployment of a containerized Python Flask web application to **AWS Fargate** using the **AWS Cloud Development Kit (CDK)** for Infrastructure as Code (IaC). The application serves as a mock analytical tool, showcasing a modern DevOps approach to building, deploying, and managing cloud-native applications.

The primary goal is to showcase expertise in **cloud infrastructure implementation**, **DevOps practices**, **CI/CD** (to be implemented), **containerization**, and **serverless architectures** on AWS.

## **Features Demonstrated (So Far)**

- **Infrastructure as Code (IaC):** AWS CDK (Python) defines and provisions all AWS resources.
- **Containerization:** Python Flask app containerized using Docker.
- **AWS Fargate:** Serverless compute for containers hosting the app.
- **Application Load Balancer (ALB):** Distributes traffic to Fargate tasks.
- **Amazon ECR:** Stores Docker image via CDK’s `from_asset`.
- **Amazon VPC:** Custom VPC setup.
- **AWS IAM:** Roles and permissions via CDK.
- **Scalable Architecture:** Resilient and cloud-native design.

## **Architecture**

The Flask backend is containerized with Docker and deployed as a **Fargate service** within a **custom VPC**, fronted by an **ALB**. All infrastructure is managed by **AWS CDK**.

### **AWS Services Used**

- Amazon ECS (Fargate)
- Application Load Balancer (ALB)
- Amazon ECR
- Amazon VPC
- AWS IAM
- AWS CloudFormation (via CDK)
- Amazon CloudWatch

### **Diagram (Mermaid Syntax)**

```mermaid
graph TD
    subgraph "User"
        U[User/Client Browser]
    end

    subgraph "AWS Cloud"
        subgraph "VPC"
            ALB[Application Load Balancer]
            subgraph "ECS Cluster (MyCluster)"
                FS[Fargate Service: MyFargateService]
                subgraph "Fargate Task 1"
                    C1[Container: stockland-app<br>(Flask + Gunicorn)]
                end
                subgraph "Fargate Task N (if scaled)"
                    CN[Container: stockland-app<br>(Flask + Gunicorn)]
                end
            end
            ECR[ECR Repository<br>(stores stockland-app image)]
        end
    end

    U -->|HTTPS Request| ALB
    ALB -->|HTTP Traffic (Port 8000)| FS
    FS --> C1
    FS --> CN
    C1 -->|Pulls image| ECR
    CN -->|Pulls image| ECR

    style U fill:#D5F5E3,stroke:#2ECC71
    style ALB fill:#AED6F1,stroke:#3498DB
    style FS fill:#FAD7A0,stroke:#F39C12
    style C1 fill:#F5B7B1,stroke:#E74C3C
    style CN fill:#F5B7B1,stroke:#E74C3C
    style ECR fill:#D2B4DE,stroke:#8E44AD
```

> _Use a Markdown previewer like VS Code with Mermaid support for this diagram._

---

## **Project Structure**

```
serverless-analytical-app/
├── .venv/                    # Python virtual environment
├── application/              # Flask app code
│   ├── app.py                # Main Flask logic
│   └── requirements.txt      # Flask dependencies
├── infrastructure/           # AWS CDK IaC code
│   ├── app.py                # CDK entry point
│   ├── cdk.json              # CDK configuration
│   ├── infrastructure_stack.py # CDK stack definition
│   └── requirements.txt      # CDK Python dependencies
├── .dockerignore             # Docker ignore file
├── .gitignore                # Git ignore file
├── Dockerfile                # Builds Flask Docker image
└── README.md                 # This file
```

---

## **Prerequisites**

- Python (3.9+)
- Node.js (Latest LTS recommended)
- AWS CDK Toolkit (`npm install -g aws-cdk`)
- AWS CLI (configured)
- Docker
- Git

---

## **Setup and Local Development**

### **Clone Repository**

```bash
git clone <your-repository-url>
cd serverless-analytical-app
```

### **Create Virtual Environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### **Install Flask App Dependencies**

```bash
pip install -r application/requirements.txt
```

### **Run Flask Locally**

```bash
cd application
python app.py
```

> Access via: http://127.0.0.1:5000

---

### **Run Docker Locally**

```bash
cd .. # Project root
docker build -t stockland-app .
docker run -p 5001:8000 --rm stockland-app
```

> Access via: http://127.0.0.1:5001

---

## **Cloud Deployment with AWS CDK**

### **Activate Environment**

```bash
source .venv/bin/activate
```

### **Install CDK Dependencies**

```bash
cd infrastructure
pip install -r requirements.txt
```

### **Configure AWS**

```bash
aws configure
```

> Enter Access Key, Secret, Region (e.g., `us-east-1`), and output format.

---

### **CDK Bootstrap (One-Time)**

```bash
cdk bootstrap aws://ACCOUNT_ID/REGION
# Example:
cdk bootstrap aws://123456789012/us-east-1
```

---

### **Synthesize CloudFormation Template**

```bash
cdk synth
```

---

### **Deploy to AWS**

```bash
cdk deploy
```

> Approve IAM changes if prompted.

---

### **Access Deployed App**

After deployment, CDK outputs the ALB DNS:

```text
http://<your-load-balancer-dns>
```

---

### **Tear Down Infrastructure**

```bash
cdk destroy
```

---

## **Key Files**

- `Dockerfile`: Flask image build and Gunicorn runner.
- `application/app.py`: Main Flask app with endpoints, defining API endpoints and serving mock analytical data.
- `infrastructure/infrastructure_stack.py`: CDK-defined AWS infra.
- `infrastructure/app.py`: CDK app entry point.
- `infrastructure/cdk.json`: CDK execution config.

---

## **Future Enhancements**

### **Phase 5: Add PostgreSQL Database**

- Integrate AWS RDS PostgreSQL.
- Connect Flask to RDS.

### **Phase 6: Implement CI/CD Pipeline**

- Automate test, build, and deploy with GitHub Actions.
