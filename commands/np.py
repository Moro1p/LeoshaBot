async def execute(cmd, ym_service):
    info = await ym_service.get_track()
    if info["success"]:
        text = f'{info["title"]} - {', '.join(info["artists"])}: {info["link"]}'
        await cmd.send(text)
    else:
        await cmd.send("Не удалось получить трек :(")