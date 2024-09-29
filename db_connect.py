import psycopg2

# Replace the placeholders with your cloud database credentials
conn = psycopg2.connect(
    host="cbdhrtd93854d5.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com",
    database="d71ofajdgo683g",
    user="uomhrls20qmv2",
    password="p6f6a7b87fe35f87c520a1d9ee97d4afb5fb997b53bcd965d0c95f6fac2347842"
)

# Your database interactions here...

conn.close()
