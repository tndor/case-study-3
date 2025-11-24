graph TD
    user(User / Browser)
    
    subgraph AWS_Cloud [AWS Cloud Region: eu-central-1]
        
        subgraph VPC [Virtual Private Cloud]
            
            subgraph Public_Subnet [Public Subnets]
                LB[Frontend Load Balancer]
                Windows[Windows Server 2019<br>Active Directory<br>(Identity Provider)]
            end
            
            subgraph Private_Subnet [Private Subnets]
                subgraph EKS_Nodes [EKS Worker Nodes]
                    
                    subgraph Pod_Frontend [Frontend Pod]
                        Nginx[Nginx Reverse Proxy]
                        React[React App Static Files]
                    end
                    
                    subgraph Pod_Backend [Backend Pod]
                        Flask[Python Flask API]
                        Exporter[Prometheus Exporter]
                    end
                    
                    subgraph Pod_Monitoring [Monitoring Namespace]
                        Prom[Prometheus]
                        Graf[Grafana]
                    end
                end
            end
        end

        subgraph AWS_Services [Managed Services]
            S3[(AWS S3<br>Home Folders)]
            DDB[(Amazon DynamoDB<br>Employee Metadata)]
            ECR[Amazon ECR<br>Container Registry]
        end
    end

    %% Network Flow
    user -- "HTTPS / Port 80" --> LB
    LB -- "Forwards Traffic" --> Nginx
    
    %% Internal App Flow (The Reverse Proxy)
    Nginx -- "Proxy /api requests<br>(ClusterIP)" --> Flask
    
    %% Backend Logic Flow
    Flask -- "LDAP (Port 389)" --> Windows
    Flask -- "Boto3 API" --> S3
    Flask -- "Boto3 API" --> DDB
    
    %% Monitoring Flow
    Prom -- "Scrapes /metrics" --> Exporter
    Graf -- "Reads Data" --> Prom
    
    %% Deployment Flow (Implicit)
    EKS_Nodes -. "Pulls Images" .- ECR

    %% Styling
    classDef aws fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:white;
    classDef k8s fill:#326CE5,stroke:#fff,stroke-width:2px,color:white;
    classDef win fill:#0078D7,stroke:#fff,stroke-width:2px,color:white;
    classDef plain fill:#fff,stroke:#333,stroke-width:1px;

    class S3,DDB,ECR,LB aws;
    class Nginx,Flask,Prom,Graf k8s;
    class Windows win;
    class user plain;