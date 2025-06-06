from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_secretsmanager as secretsmanager,
    aws_elasticloadbalancingv2 as elbv2 # Import for ALB listener conditions
)
from constructs import Construct
import os

class InfrastructureStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- 1. NETWORKING (VPC) ---
        # This remains the same, shared by all services.
        vpc = ec2.Vpc(self, "MyVPC",
            max_azs=2,
            # For higher availability in production, set nat_gateways=2
            nat_gateways=1 
        )

        # --- 2. ECS CLUSTER ---
        # A single cluster can host multiple services.
        cluster = ecs.Cluster(self, "MyCluster",
            vpc=vpc
        )

        # --- 3. DATABASE (RDS & Secrets Manager) ---
        # This is a shared resource for both applications.
        db_master_username = "postgresadmin"
        db_password_secret = secretsmanager.Secret(self, "DBPasswordSecret",
            secret_name=f"{self.stack_name}-DBPassword",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=f'{{"username": "{db_master_username}"}}',
                generate_string_key="password",
                password_length=16,
                exclude_punctuation=True
            ),
            removal_policy=RemovalPolicy.DESTROY 
        )
        
        db_instance_name = "mypostgresdb"
        
        # For High Availability, set multi_az=True
        is_prod_context = self.node.try_get_context("is_prod") # Pass -c is_prod=true for prod settings
        
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
            # For higher availability in production
            multi_az=True if is_prod_context else False,
            # For production, set a backup retention period
            backup_retention=Duration.days(7) if is_prod_context else Duration.days(0),
            delete_automated_backups=False if is_prod_context else True,
            removal_policy=RemovalPolicy.DESTROY
        )

        # --- 4. SHARED APPLICATION LOAD BALANCER ---
        # We will create an ALB and Listener manually to share them between services.
        alb = elbv2.ApplicationLoadBalancer(self, "SharedALB",
            vpc=vpc,
            internet_facing=True
        )

        # Add a default action to the listener. This handles requests that don't match any rules.
        listener = alb.add_listener("PublicListener",
            port=80,
            open=True,
            default_action=elbv2.ListenerAction.fixed_response(
                status_code=404,
                content_type="text/plain",
                message_body="Resource not found."
            )
        )

        # Output the ALB DNS name
        CfnOutput(self, "LoadBalancerDNS", value=alb.load_balancer_dns_name)
        
        # --- 5. APPLICATION DEFINITIONS (Fargate Services) ---
        
        # --- 5A. ANALYTICAL APP SERVICE (Original App) ---
        # We modify the original app's deployment to be a standalone service
        # that we can attach to the shared listener.

        analytical_app_task_def = ecs.TaskDefinition(self, "AnalyticalAppTaskDef",
            family="analytical-app",
            compatibility=ecs.Compatibility.FARGATE,
            cpu="256",
            memory_mib="512"
        )
        # Grant this specific task role access to the secret
        db_password_secret.grant_read(analytical_app_task_def.task_role)

        analytical_app_container = analytical_app_task_def.add_container("AnalyticalAppContainer",
            image=ecs.ContainerImage.from_asset(
                directory=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
                file="Dockerfile" # Assuming Dockerfile is in the root
            ),
            port_mappings=[ecs.PortMapping(container_port=8000)],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="AnalyticalApp"),
            environment={
                "DB_HOST": rds_instance.db_instance_endpoint_address,
                "DB_PORT": rds_instance.db_instance_endpoint_port,
                "DB_NAME": db_instance_name,
                "DB_USERNAME": db_master_username,
                "DB_PASSWORD_SECRET_ARN": db_password_secret.secret_arn,
                "AWS_REGION": self.region
            }
        )
        
        analytical_app_service = ecs.FargateService(self, "AnalyticalAppFargateService",
            cluster=cluster,
            task_definition=analytical_app_task_def,
            desired_count=1,
            # For scalability, you can add auto-scaling here
            # capacity_provider_strategies=[ecs.CapacityProviderStrategy(capacity_provider="FARGATE_SPOT", weight=1)] # for cost saving
        )

        # Add path-based routing for the analytical app using 'conditions'
        listener.add_targets("AnalyticalAppTarget",
            port=80,
            targets=[analytical_app_service],
            priority=1,
            conditions=[
                elbv2.ListenerCondition.path_patterns(["/api/*", "/"])
            ]
        )

        # --- 5B. NEW REPORTING APP SERVICE ---
        # Now we define the new service in a similar way.
        
        reporting_app_task_def = ecs.TaskDefinition(self, "ReportingAppTaskDef",
            family="reporting-app",
            compatibility=ecs.Compatibility.FARGATE,
            cpu="256",
            memory_mib="512"
        )
        # Grant this new task role access to the *same* secret
        db_password_secret.grant_read(reporting_app_task_def.task_role)

        reporting_app_container = reporting_app_task_def.add_container("ReportingAppContainer",
            # Point to the new Dockerfile for the reporting app
            image=ecs.ContainerImage.from_asset(
                directory=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
                file="reporting_app/Dockerfile"
            ),
            port_mappings=[ecs.PortMapping(container_port=8080)], # Matches the port in reporting_app/Dockerfile
            logging=ecs.LogDrivers.aws_logs(stream_prefix="ReportingApp"),
            environment={
                "DB_HOST": rds_instance.db_instance_endpoint_address,
                "DB_PORT": rds_instance.db_instance_endpoint_port,
                "DB_NAME": db_instance_name,
                "DB_USERNAME": db_master_username,
                "DB_PASSWORD_SECRET_ARN": db_password_secret.secret_arn,
                "AWS_REGION": self.region
            }
        )

        reporting_app_service = ecs.FargateService(self, "ReportingAppFargateService",
            cluster=cluster,
            task_definition=reporting_app_task_def,
            desired_count=1
        )
        
        # Add path-based routing for the reporting app using 'conditions'
        listener.add_targets("ReportingAppTarget",
            port=80,
            targets=[reporting_app_service],
            priority=2,
            conditions=[
                elbv2.ListenerCondition.path_patterns(["/reporting/*"])
            ],
            health_check=elbv2.HealthCheck(
                path="/reporting",  # Use a valid path for the health check
                healthy_http_codes="200" # Expect a 200 OK from the /reporting endpoint
            )
        )
        
        # --- 6. DATABASE CONNECTIVITY (SECURITY GROUPS) ---
        # Allow both services to connect to the RDS instance.
        rds_instance.connections.allow_default_port_from(analytical_app_service, "Allow Analytical App to connect to RDS")
        rds_instance.connections.allow_default_port_from(reporting_app_service, "Allow Reporting App to connect to RDS")






# from aws_cdk import (
#     Stack,
#     Duration,
#     CfnOutput,
#     RemovalPolicy,
#     aws_ec2 as ec2,
#     aws_ecs as ecs,
#     aws_ecs_patterns as ecs_patterns,
#     aws_rds as rds,
#     aws_secretsmanager as secretsmanager,
#     aws_elasticloadbalancingv2 as elbv2 # Import for ALB listener conditions
# )
# from constructs import Construct
# import os

# class InfrastructureStack(Stack):

#     def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
#         super().__init__(scope, construct_id, **kwargs)

#         # --- 1. NETWORKING (VPC) ---
#         # This remains the same, shared by all services.
#         vpc = ec2.Vpc(self, "MyVPC",
#             max_azs=2,
#             # For higher availability in production, set nat_gateways=2
#             nat_gateways=1 
#         )

#         # --- 2. ECS CLUSTER ---
#         # A single cluster can host multiple services.
#         cluster = ecs.Cluster(self, "MyCluster",
#             vpc=vpc
#         )

#         # --- 3. DATABASE (RDS & Secrets Manager) ---
#         # This is a shared resource for both applications.
#         db_master_username = "postgresadmin"
#         db_password_secret = secretsmanager.Secret(self, "DBPasswordSecret",
#             secret_name=f"{self.stack_name}-DBPassword",
#             generate_secret_string=secretsmanager.SecretStringGenerator(
#                 secret_string_template=f'{{"username": "{db_master_username}"}}',
#                 generate_string_key="password",
#                 password_length=16,
#                 exclude_punctuation=True
#             ),
#             removal_policy=RemovalPolicy.DESTROY 
#         )
        
#         db_instance_name = "mypostgresdb"
        
#         # For High Availability, set multi_az=True
#         is_prod_context = self.node.try_get_context("is_prod") # Pass -c is_prod=true for prod settings
        
#         rds_instance = rds.DatabaseInstance(self, "MyPostgresDBInstance",
#             engine=rds.DatabaseInstanceEngine.postgres(
#                 version=rds.PostgresEngineVersion.VER_15
#             ),
#             instance_type=ec2.InstanceType.of(
#                 ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
#             ),
#             vpc=vpc,
#             vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
#             credentials=rds.Credentials.from_secret(db_password_secret), 
#             database_name=db_instance_name,
#             allocated_storage=20,
#             # For higher availability in production
#             multi_az=True if is_prod_context else False,
#             # For production, set a backup retention period
#             backup_retention=Duration.days(7) if is_prod_context else Duration.days(0),
#             delete_automated_backups=False if is_prod_context else True,
#             removal_policy=RemovalPolicy.DESTROY
#         )

#         # --- 4. SHARED APPLICATION LOAD BALANCER ---
#         # We will create an ALB and Listener manually to share them between services.
#         alb = elbv2.ApplicationLoadBalancer(self, "SharedALB",
#             vpc=vpc,
#             internet_facing=True
#         )

#         # Add a default action to the listener. This handles requests that don't match any rules.
#         listener = alb.add_listener("PublicListener",
#             port=80,
#             open=True,
#             default_action=elbv2.ListenerAction.fixed_response(
#                 status_code=404,
#                 content_type="text/plain",
#                 message_body="Resource not found."
#             )
#         )

#         # Output the ALB DNS name
#         CfnOutput(self, "LoadBalancerDNS", value=alb.load_balancer_dns_name)
        
#         # --- 5. APPLICATION DEFINITIONS (Fargate Services) ---
        
#         # --- 5A. ANALYTICAL APP SERVICE (Original App) ---
#         # We modify the original app's deployment to be a standalone service
#         # that we can attach to the shared listener.

#         analytical_app_task_def = ecs.TaskDefinition(self, "AnalyticalAppTaskDef",
#             family="analytical-app",
#             compatibility=ecs.Compatibility.FARGATE,
#             cpu="256",
#             memory_mib="512"
#         )
#         # Grant this specific task role access to the secret
#         db_password_secret.grant_read(analytical_app_task_def.task_role)

#         analytical_app_container = analytical_app_task_def.add_container("AnalyticalAppContainer",
#             image=ecs.ContainerImage.from_asset(
#                 directory=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
#                 file="Dockerfile" # Assuming Dockerfile is in the root
#             ),
#             port_mappings=[ecs.PortMapping(container_port=8000)],
#             logging=ecs.LogDrivers.aws_logs(stream_prefix="AnalyticalApp"),
#             environment={
#                 "DB_HOST": rds_instance.db_instance_endpoint_address,
#                 "DB_PORT": rds_instance.db_instance_endpoint_port,
#                 "DB_NAME": db_instance_name,
#                 "DB_USERNAME": db_master_username,
#                 "DB_PASSWORD_SECRET_ARN": db_password_secret.secret_arn,
#                 "AWS_REGION": self.region
#             }
#         )
        
#         analytical_app_service = ecs.FargateService(self, "AnalyticalAppFargateService",
#             cluster=cluster,
#             task_definition=analytical_app_task_def,
#             desired_count=1,
#             # For scalability, you can add auto-scaling here
#             # capacity_provider_strategies=[ecs.CapacityProviderStrategy(capacity_provider="FARGATE_SPOT", weight=1)] # for cost saving
#         )

#         # Add path-based routing for the analytical app using 'conditions'
#         listener.add_targets("AnalyticalAppTarget",
#             port=80,
#             targets=[analytical_app_service],
#             priority=1,
#             conditions=[
#                 elbv2.ListenerCondition.path_patterns(["/api/*", "/"])
#             ]
#         )

#         # --- 5B. NEW REPORTING APP SERVICE ---
#         # Now we define the new service in a similar way.
        
#         reporting_app_task_def = ecs.TaskDefinition(self, "ReportingAppTaskDef",
#             family="reporting-app",
#             compatibility=ecs.Compatibility.FARGATE,
#             cpu="256",
#             memory_mib="512"
#         )
#         # Grant this new task role access to the *same* secret
#         db_password_secret.grant_read(reporting_app_task_def.task_role)

#         reporting_app_container = reporting_app_task_def.add_container("ReportingAppContainer",
#             # Point to the new Dockerfile for the reporting app
#             image=ecs.ContainerImage.from_asset(
#                 directory=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
#                 file="reporting_app/Dockerfile"
#             ),
#             port_mappings=[ecs.PortMapping(container_port=8080)], # Matches the port in reporting_app/Dockerfile
#             logging=ecs.LogDrivers.aws_logs(stream_prefix="ReportingApp"),
#             environment={
#                 "DB_HOST": rds_instance.db_instance_endpoint_address,
#                 "DB_PORT": rds_instance.db_instance_endpoint_port,
#                 "DB_NAME": db_instance_name,
#                 "DB_USERNAME": db_master_username,
#                 "DB_PASSWORD_SECRET_ARN": db_password_secret.secret_arn,
#                 "AWS_REGION": self.region
#             }
#         )

#         reporting_app_service = ecs.FargateService(self, "ReportingAppFargateService",
#             cluster=cluster,
#             task_definition=reporting_app_task_def,
#             desired_count=1
#         )
        
#         # Add path-based routing for the reporting app using 'conditions'
#         listener.add_targets("ReportingAppTarget",
#             port=80,
#             targets=[reporting_app_service],
#             priority=2,
#             conditions=[
#                 elbv2.ListenerCondition.path_patterns(["/reporting/*"])
#             ]
#         )
        
#         # --- 6. DATABASE CONNECTIVITY (SECURITY GROUPS) ---
#         # Allow both services to connect to the RDS instance.
#         rds_instance.connections.allow_default_port_from(analytical_app_service, "Allow Analytical App to connect to RDS")
#         rds_instance.connections.allow_default_port_from(reporting_app_service, "Allow Reporting App to connect to RDS")






# # from aws_cdk import (
# #     Stack,
# #     Duration,
# #     CfnOutput,
# #     RemovalPolicy,
# #     aws_ec2 as ec2,
# #     aws_ecs as ecs,
# #     aws_ecs_patterns as ecs_patterns,
# #     aws_rds as rds,
# #     aws_secretsmanager as secretsmanager
# # )
# # from constructs import Construct
# # import os

# # class InfrastructureStack(Stack):

# #     def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
# #         super().__init__(scope, construct_id, **kwargs)

# #         # 1. Define a VPC (Virtual Private Cloud)
# #         vpc = ec2.Vpc(self, "MyVPC",
# #             max_azs=2,
# #             nat_gateways=1 
# #         )

# #         # 2. Create an ECS Cluster
# #         cluster = ecs.Cluster(self, "MyCluster",
# #             vpc=vpc
# #         )

# #         # 3. Create a Secret for the Database Master Password
# #         db_master_username = "postgresadmin" # Define master username
# #         db_password_secret = secretsmanager.Secret(self, "DBPasswordSecret",
# #             secret_name=f"{self.stack_name}-DBPassword",
# #             generate_secret_string=secretsmanager.SecretStringGenerator(
# #                 secret_string_template=f'{{"username": "{db_master_username}"}}',
# #                 generate_string_key="password",
# #                 password_length=16,
# #                 exclude_punctuation=True
# #             ),
# #             description="Password for the RDS PostgreSQL master user",
# #             removal_policy=RemovalPolicy.DESTROY 
# #         )

# #         # 4. Create the RDS PostgreSQL Database Instance
# #         db_instance_name = "mypostgresdb" 
        
# #         # For demo purposes, setting backup_retention to 0 and delete_automated_backups to True
# #         # This makes stack destruction easier when RemovalPolicy.DESTROY is used for the DB.
# #         is_demo_context = self.node.try_get_context("is_demo") # e.g., pass -c is_demo=true
        
# #         rds_backup_retention = Duration.days(0) if is_demo_context else Duration.days(7)
# #         rds_delete_automated_backups = True if is_demo_context else False
# #         # Note: `skip_final_snapshot` is removed as it caused a TypeError, implying an older CDK lib version.
# #         # If backup_retention is 0, a final snapshot is not typically taken by default.

# #         rds_instance = rds.DatabaseInstance(self, "MyPostgresDBInstance",
# #             engine=rds.DatabaseInstanceEngine.postgres(
# #                 version=rds.PostgresEngineVersion.VER_15 
# #             ),
# #             instance_type=ec2.InstanceType.of(
# #                 ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MICRO
# #             ),
# #             vpc=vpc,
# #             vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
# #             credentials=rds.Credentials.from_secret(db_password_secret), 
# #             database_name=db_instance_name,
# #             allocated_storage=20,
# #             max_allocated_storage=50,
# #             multi_az=False,
# #             publicly_accessible=False,
# #             backup_retention=rds_backup_retention,
# #             delete_automated_backups=rds_delete_automated_backups, # Should default to True if retention is 0
# #             removal_policy=RemovalPolicy.DESTROY
# #         )

# #         # 5. Construct the path to the project root directory
# #         project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# #         # 6. Define the Fargate Service with Application Load Balancer
# #         fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "MyFargateService",
# #             cluster=cluster,
# #             cpu=256,
# #             memory_limit_mib=512,
# #             desired_count=1,
# #             task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
# #                 image=ecs.ContainerImage.from_asset(
# #                     directory=project_root_path,
# #                     build_args={ # Using build_args for wider CDK version compatibility for platform
# #                         "--platform": "linux/amd64"
# #                     }
# #                 ),
# #                 container_port=8000,
# #                 environment={
# #                     "EXAMPLE_VARIABLE": "example_value_db", 
# #                     "DB_HOST": rds_instance.db_instance_endpoint_address,
# #                     "DB_PORT": rds_instance.db_instance_endpoint_port,
# #                     "DB_NAME": db_instance_name,
# #                     "DB_USERNAME": db_master_username, # Pass the username directly
# #                     "DB_PASSWORD_SECRET_ARN": db_password_secret.secret_arn,
# #                     "AWS_REGION": self.region 
# #                 }
# #             ),
# #             public_load_balancer=True,
# #         )
        
# #         # Grant the Fargate task role permission to read the database password secret
# #         db_password_secret.grant_read(fargate_service.task_definition.task_role)

# #         # 7. Configure Security Group: Allow Fargate service to connect to RDS
# #         rds_instance.connections.allow_default_port_from(
# #             fargate_service.service.connections, 
# #             "Allow Fargate service to connect to RDS"
# #         )

# #         # 8. Configure Health Check for the Target Group
# #         fargate_service.target_group.configure_health_check(
# #             path="/", 
# #             interval=Duration.seconds(30),
# #             timeout=Duration.seconds(5),
# #             healthy_threshold_count=2,
# #             unhealthy_threshold_count=2, 
# #             healthy_http_codes="200-299"
# #         )

# #         # 9. Output values
# #         CfnOutput(self, "LoadBalancerDNS",
# #             value=fargate_service.load_balancer.load_balancer_dns_name,
# #             description="The DNS name of the Application Load Balancer"
# #         )
# #         CfnOutput(self, "DBInstanceEndpoint",
# #             value=rds_instance.db_instance_endpoint_address,
# #             description="The endpoint address of the RDS DB instance"
# #         )
# #         CfnOutput(self, "DBPasswordSecretARNOutput", # Changed output name slightly for clarity
# #             value=db_password_secret.secret_arn,
# #             description="ARN of the Secrets Manager secret for DB password"
# #         )
# #         CfnOutput(self, "DBUsernameOutput", # Outputting username for app config if needed
# #             value=db_master_username,
# #             description="Master username for the RDS database"
# #         )