import aiosqlite
DATABASE_PATH="Users.db"
class DateBase:
	def __init__(self):
		pass
	async def get_user(self, table, UserID):
		async with aiosqlite.connect(DATABASE_PATH) as db:
			db.row_factory = aiosqlite.Row  # Устанавливаем фабрику строк для получения результата в виде словаря или объекта
			cursor = await db.execute(f'SELECT * FROM {table} WHERE UserID = ?', (UserID,))
			row = await cursor.fetchone()
			if row == None:
				return 'unregister'
			return dict(row)
	async def get_user_plus(self, command):
		async with aiosqlite.connect(DATABASE_PATH) as db:
			db.row_factory = aiosqlite.Row  # Устанавливаем фабрику строк для получения результата в виде словаря или объекта
			cursor = await db.execute(command)
			row = await cursor.fetchone()
			if row == None:
				return 'unregister'
			return dict(row)
	async def cmd(self, commands):
		async with aiosqlite.connect(DATABASE_PATH) as db:
			command = await db.execute(commands)
			await db.commit()
			return await command.fetchall()
			await db.commit()
	async def get_lists(self, tables='users', table='UserID'):
		async with aiosqlite.connect(DATABASE_PATH) as db:
			command = await db.execute(f"SELECT {table} FROM {tables}")
			command = await command.fetchall()
			return command
	async def get_top(self, tables='users', table='UserID', table2='balance', limit=10):
		async with aiosqlite.connect(DATABASE_PATH) as db:
			command = await db.execute(f"SELECT {table} FROM {tables} ORDER BY {table2} DESC LIMIT {limit};")
			command = await command.fetchall()
			return command
	async def get_list_pay_history(self, cmd='off'):
		async with aiosqlite.connect(DATABASE_PATH) as db:
			command = await db.execute(cmd)
			command = await command.fetchall()
			return command
	async def get_user_list(self, UserID, tables='users', where='UserID', type='BIGINT'):
		async with aiosqlite.connect(DATABASE_PATH) as db:
			if type=='BIGINT':
				command = await db.execute(f"SELECT * FROM {tables} WHERE {where} = {UserID}")
			else:
				command = await db.execute(f"SELECT * FROM {tables} WHERE {where} = '{UserID}'")
			command = await command.fetchall()
			return command
	async def get_user2(self, UserID, tables='users', where='UserID', type='BIGINT'):
		async with aiosqlite.connect(DATABASE_PATH) as db:
			db.row_factory = aiosqlite.Row
			if type=='BIGINT':
				command = await db.execute(f"SELECT * FROM {tables} WHERE {where} = {UserID}")
			else:
				command = await db.execute(f"SELECT * FROM {tables} WHERE {where} = '{UserID}'")
			command = await command.fetchone()
			return command
	async def table(self):
		async with aiosqlite.connect(DATABASE_PATH) as db:
			with open("utils/tables.sql", "r") as sql_file:
				sql_script = sql_file.read()
			await db.executescript(sql_script)
			await db.commit()
