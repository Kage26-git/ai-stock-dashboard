import json
import os

import requests
from bs4 import BeautifulSoup

# =====================================
# 仮テーマDB
# 後で株探スクレイピングへ変更
# =====================================

def get_kabutan_theme_stocks():

    url = "https://kabutan.jp/"

    headers = {
        "User-Agent":
        "Mozilla/5.0"
    }

    response = requests.get(
        url,
        headers=headers
    )

    print(response.status_code)

    soup = BeautifulSoup(
        response.text,
        "lxml"
    )

    print(
        soup.title.text
    )

    links = soup.find_all("a")

    for link in links:

        text = link.get_text(strip=True)

        href = link.get("href")

        if href is not None:

            if "theme" in href:

                theme_url = (
                    "https://kabutan.jp"
                    + href
                )

                print(text)

                print(theme_url)

                print("==============")

    # =====================================
    # テーマページ確認
    # =====================================

    theme_urls = {

        "ai":
        "https://kabutan.jp/themes/?theme=人工知能",

        "semiconductor":
        "https://kabutan.jp/themes/?theme=半導体",

        "defense":
        "https://kabutan.jp/themes/?theme=防衛",

        "datacenter":
        "https://kabutan.jp/themes/?theme=データセンター"
    }


    theme_data = {}

    for theme_name, theme_url in theme_urls.items():

        print(f"===== {theme_name} =====")

        response = requests.get(
            theme_url,
            headers=headers
        )

        soup = BeautifulSoup(
            response.text,
            "lxml"
        )

        print(
            soup.title.text
        )

        # =====================================
        # table確認
        # =====================================

        tables = soup.find_all("table")

        print(len(tables))

        for i, table in enumerate(tables):

            print(f"===== TABLE {i} =====")

            print(
                table.text[:1000]
            )

            print("\n")
        
        target_table = tables[2]

        rows = target_table.find_all("tr")

        print(len(rows))

        for row in rows[:10]:

            print("======")

            print(
                row.get_text("\n", strip=True)
        )
        
        theme_stocks = []

        for row in rows:

            cols = row.find_all("td")

            if len(cols) >= 2:

                code = cols[0].get_text(
                    strip=True
                )

                name = cols[1].get_text(
                    strip=True
                )

                print(code, name)

                if len(code) >= 4:

                    theme_stocks.append({

                        "name": name,

                        "ticker": f"{code}.T"
                    })

        print(theme_stocks[:10])

        # =====================================
        # テーマDB化
        # =====================================

        theme_data[theme_name] = theme_stocks

    # =====================================
    # dataフォルダ作成
    # =====================================

    os.makedirs(
        "data",
        exist_ok=True
    )

    # =====================================
    # JSON保存
    # =====================================

    with open(
        "data/themes.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            theme_data,
            f,
            ensure_ascii=False,
            indent=4
        )

    print("✅ themes.json 更新完了")

    return theme_data

# =====================================
# 実行
# =====================================

get_kabutan_theme_stocks()