面と新機能の統合）
        # # 💡 新しい正規表現: /detail/{case_id} または /case/{case_id}/... のいずれにも対応
        # match_hub = re.match(r"^(/(detail|case)/(-?\d+))", e.route)
        # if match_hub:
        #     case_id = int(match_hub.group(3))  # {case_id} を取得

        #     # 💡 CaseHubView を使用して、サイドバー付きのレイアウトを構築
        #     hub_view = CaseHubView(page, case_id).build()
        #     page.views.append(hub_view)

        #     # 💡 ルート変更時のコンテンツ切り替えを明示的に呼び出す
        #     #    on_route_change の際に CaseHubView の内容を更新
        #     CaseHubView(page, case_id).route_to_content(e.route)

        # # 3. 被相続人編集ページ (/deceased_edit/<id>)
        # elif re.match(r"^/deceased_edit/(-?\d+)$", e.route):
        #     match = re.match(r"^/deceased_edit/(-?\d+)$", e.route)
        #     deceased_id = int(match.group(1))
        #     page.views.append(DeceasedEditView(page, deceased_id))

        # # 4. 相続人編集ページ (/heir_edit/<id>?deceased_id=X)
        # elif re.match(r"^/heir_edit/(\d+)(\?.*)?$", e.route):
        #     match = re.match(r"^/heir_edit/(\d+)(\?.*)?$", e.route)
        #     heir_id = int(match.group(1))

        #     # クエリパラメータから deceased_id を取得
        #     query_params = {}
        #     if match.group(2):
        #         # クエリ文字列をパース
        #         query_string = match.group(2).lstrip("?")
        #         query_params = dict(re.findall(r"([^?&=]+)=([^?&=]+)", query_string))

        #     deceased_id_from_url = int(query_params.get("deceased_id", 0))

        #     # 💡 実際の HeirEditView を呼び出す
        #     page.views.append(HeirEditView(page, heir_id, deceased_id_from_url))

        # # 5. 新規相続人追加ページ (/heir_edit/new?deceased_id=X)
        # elif re.match(r"^/heir_edit/new$", e.route) or e.route.startswith(
        #     "/heir_edit/new?"
        # ):
        #     # クエリパラメータから deceased_id を取得
        #     query_params = {}
        #     if "?" in e.route:
        #         query_string = e.route.split("?", 1)[1]
        #         query_params = dict(re.findall(r"([^?&=]+)=([^?&=]+)", query_string))

        #     deceased_id = int(query_params.get("deceased_id", 0))

        #     # 新規登録時は heir_id = 0 を渡す
        #     page.views.append