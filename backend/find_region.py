import psycopg2

regions = [
    "ap-south-1",      # Mumbai
    "ap-southeast-1",  # Singapore
    "us-east-1",       # N. Virginia
    "us-west-1",       # N. California
    "us-east-2",       # Ohio
    "us-west-2",       # Oregon
    "eu-central-1",    # Frankfurt
    "eu-west-1",       # Ireland
    "eu-west-2",       # London
    "eu-west-3",       # Paris
    "ap-northeast-1",  # Tokyo
    "ap-northeast-2",  # Seoul
    "ap-southeast-2",  # Sydney
    "sa-east-1",       # Sao Paulo
    "ca-central-1"      # Canada
]

project_ref = "wdqiqpycgvqncbebfrlr"
password = "tWVt3zebEZm7TPoR"
user = f"postgres.{project_ref}"

for region in regions:
    host = f"aws-0-{region}.pooler.supabase.com"
    print(f"Probing region {region} at {host}...")
    try:
        conn = psycopg2.connect(
            database="postgres",
            user=user,
            password=password,
            host=host,
            port="5432",
            connect_timeout=3
        )
        print(f"!!! SUCCESS !!! The correct region is: {region}")
        conn.close()
        break
    except psycopg2.OperationalError as e:
        err_msg = str(e)
        if "tenant/user" in err_msg and "not found" in err_msg:
            # This means the host is resolved, but the tenant doesn't exist in this region
            print(f"Region {region}: tenant not found.")
        elif "timeout expired" in err_msg or "could not connect" in err_msg or "Name or service not known" in err_msg:
            print(f"Region {region}: connection timeout/failure.")
        else:
            # If it failed due to password or other DB errors, it means the host/tenant IS correct!
            print(f"Region {region}: got other error (tenant matches): {err_msg}")
            break
