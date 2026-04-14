import flet as ft
import random
import asyncio

# --- МЕНЕДЖЕР ДОСТИЖЕНИЙ ---
achievements_config = {
    "first_blood": {"name": "Первая кровь", "desc": "Первая победа", "icon": "🩸"},
    "win_streak_3": {"name": "Непобедимый", "desc": "3 победы подряд (Премиум скины!)", "icon": "⚡"},
    "win_streak_5": {"name": "Легенда", "desc": "5 побед подряд", "icon": "🏆"},
    "master_tie": {"name": "Дипломат", "desc": "10 ничьих", "icon": "🤝"},
    "rock_hero": {"name": "Мастер кулака", "desc": "10 побед камнем", "icon": "🗿"},
    "stubborn": {"name": "Упёртый", "desc": "5 одинаковых жестов подряд", "icon": "🐂"},
    "unlucky": {"name": "Не твой день", "desc": "5 проигрышей подряд", "icon": "🤡"},
    "veteran": {"name": "Ветеран", "desc": "50 раундов", "icon": "🎖️"},
}


class AchievementManager:
    def __init__(self):
        self.unlocked = set()

    def check_and_unlock(self, game_state, total_games):
        new_achs = []
        checks = [
            (game_state['player_score'] >= 1, "first_blood"),
            (game_state['win_streak'] >= 3, "win_streak_3"),
            (game_state['win_streak'] >= 5, "win_streak_5"),
            (game_state['ties_count'] >= 10, "master_tie"),
            (game_state['rock_wins'] >= 10, "rock_hero"),
            (game_state['same_choice_streak'] >= 5, "stubborn"),
            (game_state['lose_streak'] >= 5, "unlucky"),
            (total_games >= 50, "veteran"),
        ]
        for condition, ach_id in checks:
            if condition and ach_id not in self.unlocked:
                self.unlocked.add(ach_id)
                new_achs.append(ach_id)
        return new_achs


achievement_manager = AchievementManager()


async def main(page: ft.Page):
    page.title = "КНБ: Грандмастер"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0a0a12"
    page.window_width = 550
    page.window_height = 1000
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    game_state = {
        "xp": 0, "level": 1, "win_streak": 0, "lose_streak": 0,
        "player_score": 0, "bot_score": 0, "ties_count": 0,
        "total_games": 0, "last_player_move": None,
        "current_skin_set": "Classic", "user_name": "Игрок",
        "rock_wins": 0, "same_choice_streak": 0, "last_choice": None
    }

    skin_sets = {
        "Classic": {"Камень": "✊", "Ножницы": "✌️", "Бумага": "✋"},
        "Premium": {"Камень": "💎", "Ножницы": "✂️", "Бумага": "📜"},
        "Nature": {"Камень": "⛰️", "Ножницы": "🦀", "Бумага": "🍃"},
        "IT": {"Камень": "🖥️", "Ножницы": "🧑‍💻", "Бумага": "📄"}
    }

    # --- UI ЭЛЕМЕНТЫ ---
    user_name_display = ft.Text(game_state["user_name"].upper(), weight="bold", size=20, color="#89b4fa")
    bot_name_display = ft.Text("БОТ", weight="bold", size=20, color="#89b4fa")
    level_text = ft.Text(f"Уровень: {game_state['level']}", size=26, weight="bold")
    xp_bar = ft.ProgressBar(value=0, width=400, color="#a6e3a1", height=6)
    xp_notif = ft.Text("", size=16, opacity=0, animate_opacity=200)
    score_display = ft.Text("ВЫ: 0  БОТ: 0  Ничьи: 0", size=20, weight="bold")
    result_text = ft.Text("Сделайте ход!", size=30, weight="bold", animate_opacity=200, color="#ff00ff")
    player_hand = ft.Text("❓", size=100, animate_scale=200)
    computer_hand = ft.Text("❓", size=100, animate_scale=200)

    def change_theme(e):
        t = e.data
        if t == "Киберпанк":
            page.bgcolor = "#0a0a12";
            result_text.color = "#ff00ff";
            score_display.color = "#00ffff"
            user_name_display.color = "#89b4fa";
            bot_name_display.color = "#89b4fa"
        elif t == "Матрица":
            page.bgcolor = "#000000";
            result_text.color = "#00ff00";
            score_display.color = "#008f11"
            user_name_display.color = "#00ff00";
            bot_name_display.color = "#00ff00"
        elif t == "Классика":
            page.bgcolor = "#f4f4f4";
            result_text.color = "#2b2b2b";
            score_display.color = "#4a4a4a"
            user_name_display.color = "#2b2b2b";
            bot_name_display.color = "#2b2b2b"
        page.update()

    async def launch_confetti():
        colors = ["#ff00ff", "#00ffff", "#ffff00", "#00ff00", "#ff0000", "#fab387"]
        particles = []
        for i in range(100):
            p = ft.Container(
                width=random.randint(7, 10),
                height=random.randint(7, 10),
                bgcolor=random.choice(colors),
                border_radius=2,
                left=random.randint(20, 430),
                top=450,
                rotate=ft.Rotate(0),
                animate_position=ft.Animation(random.randint(2000, 3500), ft.AnimationCurve.EASE_OUT_QUINT),
                animate_rotation=ft.Animation(1500, ft.AnimationCurve.LINEAR)
            )
            particles.append(p)
            game_stack.controls.append(p)
        page.update()
        await asyncio.sleep(0.01)
        for p in particles:
            p.top = 980
            p.left += random.randint(-60, 60)
            p.rotate = ft.Rotate(random.uniform(2, 6))
        page.update()
        await asyncio.sleep(4.0)
        for p in particles:
            if p in game_stack.controls:
                game_stack.controls.remove(p)
        page.update()

    async def play(choice):
        game_state["total_games"] += 1
        if choice == game_state["last_choice"]:
            game_state["same_choice_streak"] += 1
        else:
            game_state["same_choice_streak"] = 1; game_state["last_choice"] = choice

        beats = {"Камень": "Бумага", "Ножницы": "Камень", "Бумага": "Ножницы"}
        loses_to = {"Камень": "Ножницы", "Ножницы": "Бумага", "Бумага": "Камень"}
        result_text.opacity = 0
        player_hand.scale, computer_hand.scale = 0.8, 0.8
        page.update()
        await asyncio.sleep(0.05)

        diff = difficulty_dd.value
        if diff == "Невозможный" and game_state["last_player_move"]:
            comp = beats[game_state["last_player_move"]]
        elif diff == "Легкий":
            comp = loses_to[choice] if random.random() < 0.7 else random.choice(["Камень", "Ножницы", "Бумага"])
        else:
            comp = random.choice(["Камень", "Ножницы", "Бумага"])

        game_state["last_player_move"] = choice
        if choice == comp:
            res, gain, out_color = "Ничья! 🤝", 5, "#f9e2af"
            game_state["ties_count"] += 1;
            game_state["win_streak"] = 0;
            game_state["lose_streak"] = 0
        elif beats[comp] == choice:
            res, gain, out_color = "Победа! 🔥", 25, "#a6e3a1"
            game_state["player_score"] += 1;
            game_state["win_streak"] += 1;
            game_state["lose_streak"] = 0
            if choice == "Камень": game_state["rock_wins"] += 1
        else:
            res, gain, out_color = "Проигрыш 😢", 0, "#f38ba8"
            game_state["bot_score"] += 1;
            game_state["win_streak"] = 0;
            game_state["lose_streak"] += 1

        game_state["xp"] += gain
        if game_state["xp"] >= 100: game_state["xp"] -= 100; game_state["level"] += 1
        new_achs = achievement_manager.check_and_unlock(game_state, game_state["total_games"])
        if new_achs: page.run_task(launch_confetti)

        if "win_streak_3" in achievement_manager.unlocked: skin_dd.options[1].disabled = False
        if game_state["level"] >= 3: skin_dd.options[2].disabled = False
        if game_state["total_games"] >= 10: skin_dd.options[3].disabled = False

        skins = skin_sets[game_state["current_skin_set"]]
        player_hand.value, computer_hand.value = skins[choice], skins[comp]
        player_hand.scale, computer_hand.scale = 1.1, 1.1
        result_text.value = f"🔓 {achievements_config[new_achs[0]]['name']}" if new_achs else res
        result_text.opacity = 1
        score_display.value = f"{game_state['user_name'].upper()}: {game_state['player_score']}  БОТ: {game_state['bot_score']}  Ничьи: {game_state['ties_count']}"
        level_text.value = f"Уровень: {game_state['level']}";
        xp_bar.value = game_state["xp"] / 100

        history_list.controls.insert(0, ft.Container(
            content=ft.Text(f"[{diff[0]}] {skins[choice]} vs {skins[comp]} — {res}", color=out_color, weight="bold",
                            size=14), bgcolor="#1e1e2e", padding=10, border_radius=10,
            border=ft.border.all(1, out_color)))
        page.update()
        if gain > 0:
            xp_notif.value = f"+{gain} XP!";
            xp_notif.opacity = 1;
            page.update()
            await asyncio.sleep(0.6);
            xp_notif.opacity = 0;
            page.update()

    # --- ИНТЕРФЕЙС ---
    name_input = ft.TextField(label="Ник", value="Игрок", width=180, text_size=15, content_padding=10,
                              on_change=lambda e: (game_state.update({"user_name": e.data or "Игрок"}),
                                                   setattr(user_name_display, "value", game_state["user_name"].upper()),
                                                   page.update()))
    theme_dd = ft.Dropdown(label="Тема", value="Киберпанк", width=180, text_size=15,
                           options=[ft.dropdown.Option("Киберпанк"), ft.dropdown.Option("Матрица"),
                                    ft.dropdown.Option("Классика")], on_change=change_theme)
    difficulty_dd = ft.Dropdown(label="Сложность", value="Средний", width=150, text_size=15,
                                options=[ft.dropdown.Option("Легкий"), ft.dropdown.Option("Средний"),
                                         ft.dropdown.Option("Невозможный")])
    skin_dd = ft.Dropdown(label="Скины", value="Classic", width=150, text_size=15,
                          options=[ft.dropdown.Option("Classic"), ft.dropdown.Option("Premium", disabled=True),
                                   ft.dropdown.Option("Nature", disabled=True),
                                   ft.dropdown.Option("IT", disabled=True)],
                          on_change=lambda e: (game_state.update({"current_skin_set": e.data}), update_button_emojis()))
    history_list = ft.ListView(spacing=10, auto_scroll=True, height=160, padding=10)

    def update_button_emojis():
        skins = skin_sets[game_state["current_skin_set"]]
        btn_rock.content.controls[0].value, btn_scissors.content.controls[0].value, btn_paper.content.controls[
            0].value = skins["Камень"], skins["Ножницы"], skins["Бумага"]
        page.update()

    async def show_achievements(e):
        ach_list = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=450)
        for ach_id, data in achievements_config.items():
            is_un = ach_id in achievement_manager.unlocked
            ach_list.controls.append(ft.Container(content=ft.Row([ft.Text(data['icon'], size=30), ft.Column(
                [ft.Text(data['name'], weight="bold", size=14, color="#cdd6f4" if is_un else "#6c7086"),
                 ft.Text(data['desc'], size=12, color="#6c7086")], expand=True), ft.Icon(
                ft.Icons.CHECK_CIRCLE if is_un else ft.Icons.LOCK, size=20, color="#a6e3a1" if is_un else "#f38ba8")]),
                                                  padding=10, border_radius=10,
                                                  bgcolor="#1a1a2e" if is_un else "#11111b",
                                                  opacity=1.0 if is_un else 0.5))
        dlg = ft.AlertDialog(title=ft.Text("🏆 Достижения", size=22, weight="bold"),
                             content=ft.Container(content=ach_list, width=400), actions=[
                ft.TextButton("Закрыть", on_click=lambda _: (setattr(dlg, "open", False), page.update()))])
        page.overlay.append(dlg);
        dlg.open = True;
        page.update()

    # --- КНОПКИ (УМЕНЬШЕННЫЕ) ---
    def create_choice_btn(text, color):
        emoji = skin_sets[game_state["current_skin_set"]][text]
        return ft.Container(
            content=ft.Column([ft.Text(emoji, size=45), ft.Text(text, size=13, weight="bold", color="#11111b")],
                              alignment="center", horizontal_alignment="center", spacing=2),
            bgcolor=color, width=100, height=120, border_radius=15,
            on_click=lambda _: page.run_task(play, text),
            on_hover=lambda e: (setattr(e.control, "scale", 1.1 if e.data == "true" else 1.0), e.control.update()),
            animate_scale=200
        )

    btn_rock, btn_scissors, btn_paper = create_choice_btn("Камень", "#89b4fa"), create_choice_btn("Ножницы",
                                                                                                  "#cba6f7"), create_choice_btn(
        "Бумага", "#f9e2af")

    game_ui = ft.Column([
        ft.Text("КНБ: ГРАНДМАСТЕР 0.27", size=32, weight="bold", color="#89b4fa"),
        ft.Row([name_input, theme_dd], alignment="center", spacing=15),
        ft.Row([level_text, xp_notif], alignment="center", spacing=20),
        xp_bar, score_display,
        ft.Row([difficulty_dd, skin_dd], alignment="center", spacing=15),
        result_text,
        ft.Row([ft.Column([user_name_display, player_hand], horizontal_alignment="center"),
                ft.Text("VS", size=24, color="#6c7086", weight="bold"),
                ft.Column([bot_name_display, computer_hand], horizontal_alignment="center")], alignment="spaceEvenly",
               width=450),
        ft.Row([btn_rock, btn_scissors, btn_paper], alignment="center", spacing=15),
        ft.ElevatedButton("🏆 ДОСТИЖЕНИЯ", on_click=show_achievements, bgcolor="#fab387", color="#11111b", height=45,
                          width=200),
        ft.Container(content=history_list, bgcolor="#11111b", padding=5, border_radius=15, width=450,
                     border=ft.border.all(1, "#313244")),
        ft.Row([ft.TextButton("Очистить логи", on_click=lambda _: (history_list.controls.clear(), page.update()),
                              style=ft.ButtonStyle(color="#f38ba8")), ft.ElevatedButton("Сброс счета",
                                                                                        on_click=lambda _: (
                                                                                            game_state.update(
                                                                                                {"player_score": 0,
                                                                                                 "bot_score": 0,
                                                                                                 "ties_count": 0}),
                                                                                            page.update()),
                                                                                        bgcolor="#f38ba8",
                                                                                        color="white", height=35)],
               alignment="center", spacing=15)
    ], horizontal_alignment="center", spacing=15, width=450)

    game_stack = ft.Stack([game_ui], width=450, expand=True, alignment=ft.alignment.center)
    page.add(game_stack)


if __name__ == "__main__":
    ft.app(target=main)