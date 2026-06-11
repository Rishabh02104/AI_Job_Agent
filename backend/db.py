from supabase import create_client, Client
from config import settings

# Initialize the Supabase Client using the service_role key to bypass RLS in trusted backend operations
supabase: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

# Admin alias for backwards compatibility
supabase_admin: Client = supabase
