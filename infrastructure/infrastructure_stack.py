from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager
)
from constructs import Construct
import os

class InfrastructureStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Define a VPC (Virtual Private Cloud)
        vpc = ec2.Vpc(self, "MyVPC",
            max_azs=2,
            nat_gateways=1 
        )

        # 2. Create an ECS Cluster
        cluster = ecs.Cluster(self, "MyCluster",
            vpc=vpc
        )

        # 3. Create a Secret for the Database Master Password
        db_master_username = "postgresadmin" # Define master username
        db_password_secret = secretsmanager.Secret(self, "DBPasswordSecret",
            secret_name=f"{self.stack_name}-DBPassword",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=f'{{"username": "{db_master_username}"}}',
                generate_string_key="password",
                password_length=16,
                exclude_punctuation=True
            ),
            description="Password for the RDS PostgreSQL master user",
            removal_policy=RemovalPolicy.DESTROY 
        )

        # 4. Create the RDS PostgreSQL Database Instance
        db_instance_name = "mypostgresdb" 
        
        # For demo purposes, setting backup_retention to 0 and delete_automated_backups to True
        # This makes stack destruction easier when RemovalPolicy.DESTROY is used for the DB.
        is_demo_context = self.node.try_get_context("is_demo") # e.g., pass -c is_demo=true
        
        rds_backup_retention = Duration.days(0) if is_demo_context else Duration.days(7)
        rds_delete_automated_backups = True if is_demo_context else False
        # Note: `skip_final_snapshot` is removed as it caused a TypeError, implying an older CDK lib version.
        # If backup_retention is 0, a final snapshot is not typically taken by default.

        rds_instance = rds.DatabaseInstance(self, "MyPostgresDBInstance",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15 
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            credentials=rds.Credentials.from_secret(db_password_secret), 
            database_name=db_instance_name,
            allocated_storage=20,
            max_allocated_storage=50,
            multi_az=False,
            publicly_accessible=False,
            backup_retention=rds_backup_retention,
            delete_automated_backups=rds_delete_automated_backups, # Should default to True if retention is 0
            removal_policy=RemovalPolicy.DESTROY
        )

        # 5. Construct the path to the project root directory
        project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # 6. Define the Fargate Service with Application Load Balancer
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "MyFargateService",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_asset(
                    directory=project_root_path,
                    build_args={ # Using build_args for wider CDK version compatibility for platform
                        "--platform": "linux/amd64"
                    }
                ),
                container_port=8000,
                environment={
                    "EXAMPLE_VARIABLE": "example_value_db", 
                    "DB_HOST": rds_instance.db_instance_endpoint_address,
                    "DB_PORT": rds_instance.db_instance_endpoint_port,
                    "DB_NAME": db_instance_name,
                    "DB_USERNAME": db_master_username, # Pass the username directly
                    "DB_PASSWORD_SECRET_ARN": db_password_secret.secret_arn,
                    "AWS_REGION": self.region 
                }
            ),
            public_load_balancer=True,
        )
        
        # Grant the Fargate task role permission to read the database password secret
        db_password_secret.grant_read(fargate_service.task_definition.task_role)

        # 7. Configure Security Group: Allow Fargate service to connect to RDS
        rds_instance.connections.allow_default_port_from(
            fargate_service.service.connections, 
            "Allow Fargate service to connect to RDS"
        )

        # 8. Configure Health Check for the Target Group
        fargate_service.target_group.configure_health_check(
            path="/", 
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=2, 
            healthy_http_codes="200-299"
        )

        # 9. Output values
        CfnOutput(self, "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name,
            description="The DNS name of the Application Load Balancer"
        )
        CfnOutput(self, "DBInstanceEndpoint",
            value=rds_instance.db_instance_endpoint_address,
            description="The endpoint address of the RDS DB instance"
        )
        CfnOutput(self, "DBPasswordSecretARNOutput", # Changed output name slightly for clarity
            value=db_password_secret.secret_arn,
            description="ARN of the Secrets Manager secret for DB password"
        )
        CfnOutput(self, "DBUsernameOutput", # Outputting username for app config if needed
            value=db_master_username,
            description="Master username for the RDS database"
        )