import argparse
import csv
import itertools
from dataclasses import dataclass
from typing import Dict, Generator, List, Set, Tuple

import pyperclip
from googleapiclient.errors import HttpError

from google_sheets_api import GoogleSheetsAPI


@dataclass
class Ingredient:
    name: str
    quantity: float
    unit: str
    location: str
    duration: float

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, __value: object) -> bool:
        if type(__value) == Ingredient:
            return self.name == __value.name
        else:
            return False


# unit / liter
VOLUME_UNITS = {
    "tbsp": 0.0147868,
    "tsp": 0.00492892,
    "cup": 0.236588,
    "oz": 0.0295735,
}

# unit / kg
MASS_UNITS = {
    "g": 1e-3,
    "kg": 1.0,
    "lb": 0.453592,
    "oz": 0.0283495,
}


def convert_units(unit1: str, unit2: str) -> float:
    # find conversion from unit2 to unit1
    unit1 = unit1.lower()
    unit2 = unit2.lower()
    if unit1 == unit2:
        return 1.0
    elif unit1 in VOLUME_UNITS and unit2 in VOLUME_UNITS:
        return VOLUME_UNITS[unit1] / VOLUME_UNITS[unit2]
    elif unit1 in MASS_UNITS and unit2 in MASS_UNITS:
        return MASS_UNITS[unit1] / MASS_UNITS[unit2]
    else:
        return float("nan")


def load_local_table() -> Generator[Tuple[str, ...], None, None]:
    with open("ingredients.csv", newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for row in reader:
            yield tuple(row)


def load_google_table() -> Generator[Tuple[str, ...], None, None]:
    api = GoogleSheetsAPI("Ingredients!A1:F")
    return api.load_table()


def save_ingredients(
    table: Generator[Tuple[str, ...], None, None]
) -> Generator[Tuple[str, ...], None, None]:
    table, table_copy = itertools.tee(table)
    with open("ingredients.csv", "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=",", quotechar='"')
        for row in table_copy:
            writer.writerow(row)
    return table


def load_ingredients(
    table: Generator[Tuple[str, ...], None, None]
) -> Tuple[Dict[str, List[Ingredient]], Set[str]]:
    header = next(table)
    current_recipe = ""
    recipes = {}
    bulk_items = set()
    for row in table:
        recipe_name = row[0].strip()
        if len(recipe_name) != 0:
            current_recipe = recipe_name
        duration = row[5].strip()
        if duration == "indefinite":
            duration = float("nan")
        else:
            duration = 0.0 if len(duration) == 0 else float(duration)
        ingredient = Ingredient(
            name=row[1].lower().strip(),
            quantity=0.0 if len(row[2]) == 0 else float(row[2]),
            unit=row[3].strip(),
            location=row[4].strip(),
            duration=duration,
        )

        if current_recipe not in recipes:
            recipes[current_recipe] = []
        recipes[current_recipe].append(ingredient)

        if duration != duration:
            bulk_items.add(ingredient.name)
    return recipes, bulk_items


def build_shopping_cart_table(
    query: List[str], recipes: Dict[str, List[Ingredient]], bulk_items: Set[str]
) -> List[List[str]]:
    table = [["Plan 0"]]

    shopping_list: List[Ingredient] = []
    for key in query:
        table.append([key])
        for ingredient in recipes[key]:
            if ingredient not in shopping_list:
                shopping_list.append(ingredient)
            else:
                stored = shopping_list[shopping_list.index(ingredient)]
                conversion = convert_units(stored.unit, ingredient.unit)
                if conversion != conversion:  # is nan
                    print(
                        f"Incompatible units for {ingredient}. {stored.unit} != {ingredient.unit}"
                    )
                else:
                    if conversion != 1.0:
                        quantity = round(ingredient.quantity * conversion, 2)
                    else:
                        quantity = ingredient.quantity
                    stored.quantity += quantity
    table.append([])
    table.append(["Ingredients", "", "", "Pantry"])

    main_ingredient_table = []
    for ingredient in shopping_list:
        if ingredient.name in bulk_items:
            continue
        main_ingredient_table.append(ingredient_row(ingredient))
    pantry_ingredient_table = []
    for ingredient in shopping_list:
        if ingredient.name in bulk_items:
            pantry_ingredient_table.append(ingredient_row(ingredient))

    for index in range(max(len(main_ingredient_table), len(pantry_ingredient_table))):
        if index < len(main_ingredient_table):
            main_row = main_ingredient_table[index]
        else:
            main_row = ["", "", ""]
        if index < len(pantry_ingredient_table):
            pantry_row = pantry_ingredient_table[index]
        else:
            pantry_row = ["", "", ""]
        table.append(main_row + pantry_row)

    return table


def ingredient_row(ingredient: Ingredient) -> List[str]:
    if len(ingredient.unit.strip()) == 0:
        return [str(ingredient.name)]
    else:
        if ingredient.unit == "count":
            quantity = int(ingredient.quantity)
        else:
            quantity = ingredient.quantity
        return [str(x) for x in (ingredient.name, quantity, ingredient.unit)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "query",
        nargs="*",
        default="",
        help="A list of recipes to make, comma separated. If not provided, the clipboard will be used.",
    )
    args = parser.parse_args()

    query_arg: List[str] = args.query

    if len(args.query) > 0:
        merged = " ".join(query_arg)
        query = [q for q in merged.split(",") if len(q.strip()) > 0]
    else:
        query = pyperclip.paste().strip().splitlines()
    print("Using query:")
    print(query)
    try:
        ingredients = load_google_table()
        ingredients = save_ingredients(ingredients)
    except HttpError as e:
        print(f"Error loading google table. Loading local table instead. {e}")
        ingredients = load_local_table()

    recipes, bulk_items = load_ingredients(ingredients)
    table = build_shopping_cart_table(query, recipes, bulk_items)
    result = ""
    for row in table:
        result += "\t".join(row) + "\n"
    pyperclip.copy(result)
    print(result)
    print("Copied to clipboard")


if __name__ == "__main__":
    main()
