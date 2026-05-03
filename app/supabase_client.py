from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = create_client(
                os.getenv('SUPABASE_URL'),
                os.getenv('SUPABASE_KEY')
            )
        return cls._instance
    
    def get_client(self) -> Client:
        return self.client
    
    def upload_image(self, file, bucket='products', path=None):
        """Upload image to Supabase Storage"""
        if path is None:
            path = f"{datetime.now().timestamp()}_{file.filename}"
        
        response = self.client.storage.from_(bucket).upload(path, file)
        if response:
            public_url = self.client.storage.from_(bucket).get_public_url(path)
            return public_url
        return None
    
    def get_products(self, filters=None):
        """Get products from Supabase"""
        query = self.client.table('products').select('*')
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        return query.execute()
    
    def create_order(self, order_data):
        """Create order in Supabase"""
        return self.client.table('orders').insert(order_data).execute()
    
    def update_order_status(self, order_id, status):
        """Update order status"""
        return self.client.table('orders').update({'status': status}).eq('id', order_id).execute()

supabase = SupabaseClient()