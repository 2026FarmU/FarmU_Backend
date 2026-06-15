from sqlalchemy import text


async def seed_base(db_session) -> None:
    await db_session.execute(
        text("INSERT INTO unions(id, code, name) VALUES ('uni_001','U001','테스트조합')")
    )
    await db_session.execute(
        text(
            "INSERT INTO users(id, login_id, hashed_password, name, role, union_id, is_withdrawn, created_at) VALUES ('usr_001','admin','x','관리자','UNION_ADMIN','uni_001',false,NOW()), ('usr_mem','member','x','조합원','MEMBER','uni_001',false,NOW())"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO members(id, union_id, name, group_name, main_crop, region, created_at) VALUES ('mem_001','uni_001','김농부','LOW','사과','대구',NOW()), ('mem_002','uni_001','박멘토','TOP','사과','경산',NOW())"
        )
    )
    await db_session.execute(
        text("INSERT INTO user_member_links(user_id, member_id) VALUES ('usr_mem','mem_001')")
    )
    await db_session.execute(
        text(
            "INSERT INTO member_performances(member_id, union_id, period, rank, score, score_delta, production_score, shipping_score, revenue_score, production_weight, shipping_weight, revenue_weight, production_percentile, shipping_percentile, revenue_percentile) VALUES ('mem_001','uni_001','2026-05',2,65,1,20,22,23,35,35,30,40,45,50), ('mem_002','uni_001','2026-05',1,91,2,31,30,30,35,35,30,95,93,92)"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO lands(id, union_id, member_id, name, pnu, address, latitude, longitude, area, main_crop, created_at) VALUES ('land_001','uni_001','mem_001','동쪽밭','1234567890123456789','대구 동구',35.8,128.6,1200,'사과',NOW())"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO land_suitabilities(land_id, crop, score, reasons) VALUES ('land_001','복숭아',88,'[\"토양 적합\", \"일조량 양호\"]')"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO notifications(id, user_id, type, title, message, level, is_read, action_url, created_at) VALUES ('noti_001','usr_001','RISK_ALERT','위험 알림','가격 확인','HIGH',false,'/dashboard?focus=alerts',NOW())"
        )
    )
    await db_session.commit()


async def test_member_land_scenario_and_mentoring(app_client, db_session, make_token):
    await seed_base(db_session)
    admin = make_token("usr_001", "UNION_ADMIN", "uni_001")
    member = make_token("usr_mem", "MEMBER", "uni_001")

    me = await app_client.get(
        "/api/v1/members/me/analysis", headers={"Authorization": f"Bearer {member}"}
    )
    assert me.status_code == 200
    assert me.json()["data"]["memberId"] == "mem_001"
    assert me.json()["data"]["period"] == "2026-05"

    lands = await app_client.get("/api/v1/lands", headers={"Authorization": f"Bearer {admin}"})
    suitability = await app_client.get(
        "/api/v1/lands/land_001/suitability", headers={"Authorization": f"Bearer {admin}"}
    )
    assert lands.json()["data"][0]["landId"] == "land_001"
    assert suitability.json()["data"]["candidates"][0]["score"] == 88

    payload = {
        "memberId": "mem_001",
        "landId": "land_001",
        "changes": {
            "fromCrop": "사과",
            "toCrop": "복숭아",
            "applyAreaRatio": 0.5,
            "startPeriod": "2026-06",
        },
    }
    simulated = await app_client.post(
        "/api/v1/scenarios/simulate", json=payload, headers={"Authorization": f"Bearer {admin}"}
    )
    scenario_id = simulated.json()["data"]["scenarioId"]
    saved = await app_client.post(
        "/api/v1/scenarios",
        json={"scenarioId": scenario_id, "name": "복숭아 전환"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    listed = await app_client.get("/api/v1/scenarios", headers={"Authorization": f"Bearer {admin}"})
    assert simulated.status_code == 200
    assert saved.status_code == 201
    assert listed.json()["data"][0]["name"] == "복숭아 전환"
    assert listed.json()["data"][0]["landId"] == "land_001"

    suggestions = await app_client.get(
        "/api/v1/mentoring/suggestions",
        params={"menteeId": "mem_001"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    mentor_detail = await app_client.get(
        "/api/v1/mentoring/suggestions/mem_002",
        params={"menteeId": "mem_001"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    match = await app_client.post(
        "/api/v1/mentoring/matches",
        json={"menteeId": "mem_001", "mentorId": "mem_002", "goal": "생산량 개선"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    match_id = match.json()["data"]["matchId"]
    approved = await app_client.patch(
        f"/api/v1/mentoring/matches/{match_id}/approve",
        headers={"Authorization": f"Bearer {admin}"},
    )
    task = await app_client.post(
        f"/api/v1/mentoring/matches/{match_id}/tasks",
        json={"title": "토양 검사", "dueDate": "2026-06-30"},
        headers={"Authorization": f"Bearer {admin}"},
    )
    task_id = task.json()["data"]["taskId"]
    updated_task = await app_client.patch(
        f"/api/v1/mentoring/matches/{match_id}/tasks/{task_id}",
        json={"completed": True},
        headers={"Authorization": f"Bearer {admin}"},
    )
    tasks = await app_client.get(
        f"/api/v1/mentoring/matches/{match_id}/tasks",
        headers={"Authorization": f"Bearer {admin}"},
    )
    assert suggestions.json()["data"][0]["mentorId"] == "mem_002"
    assert suggestions.json()["data"][0]["matchReasons"]
    assert mentor_detail.json()["data"]["matchFactors"]
    assert mentor_detail.json()["data"]["comparison"][0]["category"] == "PRODUCTION"
    assert mentor_detail.json()["data"]["helpAreas"][0]["title"]
    assert approved.json()["data"]["status"] == "APPROVED"
    assert updated_task.json()["data"]["completed"] is True
    assert tasks.json()["data"][0]["taskId"] == task_id

    removed = await app_client.delete(
        f"/api/v1/scenarios/{scenario_id}", headers={"Authorization": f"Bearer {admin}"}
    )
    assert removed.status_code == 204


async def test_reports_data_weights_notifications_and_search(app_client, db_session, make_token):
    await seed_base(db_session)
    token = make_token("usr_001", "UNION_ADMIN", "uni_001")
    headers = {"Authorization": f"Bearer {token}"}

    report = await app_client.post(
        "/api/v1/reports/generate",
        json={
            "type": "MEMBER",
            "format": "PDF",
            "sections": ["SUMMARY", "XAI"],
            "period": "2026-05",
            "unionId": "uni_001",
            "memberId": "mem_001",
        },
        headers=headers,
    )
    report_id = report.json()["data"]["jobId"]
    detail = await app_client.get(f"/api/v1/reports/{report_id}", headers=headers)
    download = await app_client.get(detail.json()["data"]["downloadUrl"])
    assert report.status_code == 202
    assert detail.json()["data"]["downloadUrlExpiresAt"]
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"

    upload = await app_client.post(
        "/api/v1/data/uploads",
        json={"fileName": "members.csv", "dataType": "text/csv", "size": 20},
        headers=headers,
    )
    upload_id = upload.json()["data"]["uploadId"]
    uploaded = await app_client.put(
        upload.json()["data"]["uploadUrl"],
        content=b"name,crop\nkim,apple\n",
        headers={"Content-Type": "text/csv"},
    )
    validation = await app_client.get(
        f"/api/v1/data/uploads/{upload_id}/validation", headers=headers
    )
    revalidated = await app_client.post(
        f"/api/v1/data/uploads/{upload_id}/revalidate", headers=headers
    )
    history = await app_client.get("/api/v1/data/uploads", headers=headers)
    applied = await app_client.post(f"/api/v1/data/uploads/{upload_id}/commit", headers=headers)
    assert uploaded.status_code == 200
    assert validation.json()["data"]["valid"] is True
    assert revalidated.json()["data"]["status"] == "VALIDATED"
    assert history.json()["data"][0]["uploadId"] == upload_id
    assert applied.json()["data"]["status"] == "APPLIED"

    weights = await app_client.patch(
        "/api/v1/settings/weights",
        json={"production": 40, "shipping": 30, "revenue": 30},
        headers=headers,
    )
    assert weights.json()["data"]["production"] == 40

    unread = await app_client.get("/api/v1/notifications/unread-count", headers=headers)
    await app_client.patch("/api/v1/notifications/noti_001/read", headers=headers)
    unread_after = await app_client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread.json()["data"]["unreadCount"] == 1
    assert unread_after.json()["data"]["unreadCount"] == 0

    search = await app_client.get("/api/v1/search", params={"q": "김농"}, headers=headers)
    assert search.json()["data"][0]["type"] == "MEMBER"

    profile = await app_client.patch(
        "/api/v1/users/me",
        json={
            "name": "새관리자",
            "phone": "010-1234-5678",
            "email": "admin@farmu.kr",
            "bio": "운영자",
        },
        headers=headers,
    )
    settings = await app_client.put(
        "/api/v1/users/me/notifications",
        json={"settings": [{"key": "RISK_ALERT", "channels": ["PUSH"], "enabled": True}]},
        headers=headers,
    )
    image = await app_client.patch(
        "/api/v1/users/me/images",
        files={"avatar": ("avatar.png", b"png", "image/png")},
        headers=headers,
    )
    profile_get = await app_client.get("/api/v1/users/me", headers=headers)
    assert profile.status_code == 200
    assert settings.status_code == 204
    assert image.json()["data"]["avatarUrl"]
    assert profile_get.json()["data"]["phone"] == "010-1234-5678"
