import flet as ft
import requests
import psycopg2
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
username = config['DEFAULT']['username']
password = config['DEFAULT']['password']

api_key = config['DEFAULT']['api_key']
base_url = 'https://api.spoonacular.com/'

def get_todays_totals(conn):

    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT SUM(calories), SUM(fat), SUM(protein), SUM(carbs) 
            FROM meals 
            WHERE date_eaten = CURRENT_DATE
        """)
        return cursor.fetchone()

def get_weekly_averages(conn):
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT AVG(calories), AVG(fat), AVG(protein), AVG(carbs) 
            FROM meals 
            WHERE date_eaten > CURRENT_DATE - INTERVAL '7 days'
        """)
        return cursor.fetchone()

def search_food(query):
    endpoint = 'food/ingredients/search'
    params = {'query': query, 'apiKey': api_key}
    response = requests.get(base_url + endpoint, params=params)
    return response.json()

def get_nutrition(food_id):
    endpoint = f'food/ingredients/{food_id}/information'
    params = {'amount': 100, 'unit': 'grams', 'apiKey': api_key}
    response = requests.get(base_url + endpoint, params=params)
    return response.json()

# Main function to set up the Flet app interface
def main(page: ft.Page):
    page.title = "Nutrition Tracker"

    # Handle the nutrition data of the first result from a food search
    def get_first_food_nutrition(food_items):
        if food_items:
            first_item = food_items[0]
            food_id = first_item['id']
            nutrition = get_nutrition(food_id)
            food_data = {
                'name': nutrition.get('name', ''),
                'calories': next((n['amount'] for n in nutrition['nutrition']['nutrients'] if n['name'] == 'Calories'), 0),
                'fat': next((n['amount'] for n in nutrition['nutrition']['nutrients'] if n['name'] == 'Fat'), 0),
                'protein': next((n['amount'] for n in nutrition['nutrition']['nutrients'] if n['name'] == 'Protein'), 0),
                'carbs': next((n['amount'] for n in nutrition['nutrition']['nutrients'] if n['name'] == 'Carbohydrates'), 0),
            }
            add_meal_to_db(food_data)
            update_nutritional_data()

    def on_submit(e):
        food_item = food_search_input.value
        results = search_food(food_item)
        get_first_food_nutrition(results.get('results', []))

    food_search_input = ft.TextField(label="Search for Food")
    submit_button = ft.ElevatedButton("Search", on_click=on_submit)

    page.add(food_search_input, submit_button)

    #
    today_totals_label = ft.Text("Today's Nutritional Totals:")
    today_totals_data = ft.Text("")  # Placeholder for actual data
    page.add(today_totals_label, today_totals_data)

    # Weekly Averages UI Elements
    weekly_averages_label = ft.Text("Weekly Nutritional Averages:")
    weekly_averages_data = ft.Text("")  # Placeholder for actual data
    page.add(weekly_averages_label, weekly_averages_data)

    # Update the nutritional data displayed in the UI
    def update_nutritional_data():
        conn = psycopg2.connect(database="nutrition_tracker", user=username,
                                password= password)  # Use your actual connection details
        today_totals = get_todays_totals(conn)

        weekly_averages = get_weekly_averages(conn)

        conn.close()

        if today_totals:
            today_totals_data.value = f"Calories: {today_totals[0]}, Fat: {today_totals[1]}g, Protein: {today_totals[2]}g, Carbs: {today_totals[3]}g"
            today_totals_data.update()
        if weekly_averages:
            weekly_averages_data.value = f"Calories: {weekly_averages[0]:.1f}, Fat: {weekly_averages[1]:.1f}g, Protein: {weekly_averages[2]:.1f}g, Carbs: {weekly_averages[3]:.1f}g"
            weekly_averages_data.update()

    # Add a meal's nutritional data to the database
    def add_meal_to_db(food_data):
        conn = psycopg2.connect(database="nutrition_tracker", user= username, password= password)  # Update with your credentials
        cursor = conn.cursor()

        try:
            food_name = food_data['name']
            calories = int(food_data['calories'])  # Ensuring calories is an integer
            fat = float(food_data['fat'])  # Ensuring fat is a double precision (float)
            protein = float(food_data['protein'])  # Ensuring protein is a double precision (float)
            carbs = float(food_data['carbs'])  # Ensuring carbs is a double precision (float)

            cursor.execute(
                "INSERT INTO meals (food_name, calories, fat, protein, carbs, date_eaten, time_eaten) VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, CURRENT_TIME)",
                (food_name, calories, fat, protein, carbs)
            )
            conn.commit()
        except Exception as e:
            print(f"Error inserting into DB: {e}")
        finally:
            conn.close()


ft.app(target=main)
