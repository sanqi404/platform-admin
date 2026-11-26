-- RBAC 管理平台底座 · 初始化脚本（SQLITE）
-- 由 ORM 模型与种子数据导出，与 backend/alembic 迁移保持一致。
-- 用法：sqlite3 rbac.db < 01_schema.sql，再执行 02_seed.sql


-- ---------------------------------------------------------------- 表结构

CREATE TABLE sys_tenant (
	id INTEGER NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	contact VARCHAR(64), 
	phone VARCHAR(32), 
	status INTEGER NOT NULL, 
	max_users INTEGER NOT NULL, 
	expire_at DATETIME, 
	remark VARCHAR(255), 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE sys_permission (
	id INTEGER NOT NULL, 
	code VARCHAR(128) NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	module VARCHAR(64) NOT NULL, 
	"group" VARCHAR(64) NOT NULL, 
	sort INTEGER NOT NULL, 
	remark VARCHAR(255), 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE sys_menu (
	id INTEGER NOT NULL, 
	parent_id INTEGER NOT NULL, 
	title VARCHAR(64) NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	path VARCHAR(128) NOT NULL, 
	component VARCHAR(128) NOT NULL, 
	icon VARCHAR(64), 
	type VARCHAR(16) NOT NULL, 
	perm_code VARCHAR(128), 
	sort INTEGER NOT NULL, 
	visible BOOLEAN NOT NULL, 
	keep_alive BOOLEAN NOT NULL, 
	is_ext BOOLEAN NOT NULL, 
	status INTEGER NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE sys_dept (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	parent_id INTEGER NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	leader VARCHAR(64), 
	sort INTEGER NOT NULL, 
	status INTEGER NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_dept_tenant_name UNIQUE (tenant_id, name, parent_id)
);

CREATE TABLE sys_role (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	data_scope INTEGER NOT NULL, 
	custom_dept_ids JSON NOT NULL, 
	status INTEGER NOT NULL, 
	is_system BOOLEAN NOT NULL, 
	is_all_perm BOOLEAN NOT NULL DEFAULT 0, 
	sort INTEGER NOT NULL, 
	remark VARCHAR(255), 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_role_tenant_code UNIQUE (tenant_id, code), 
	FOREIGN KEY(tenant_id) REFERENCES sys_tenant (id) ON DELETE CASCADE
);

CREATE TABLE sys_user (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	dept_id INTEGER, 
	username VARCHAR(64) NOT NULL, 
	nickname VARCHAR(64) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	email VARCHAR(128), 
	phone VARCHAR(32), 
	avatar VARCHAR(255), 
	status INTEGER NOT NULL, 
	is_superuser BOOLEAN NOT NULL, 
	login_fail_count INTEGER NOT NULL, 
	locked_until DATETIME, 
	last_login_at DATETIME, 
	last_login_ip VARCHAR(64), 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_tenant_username UNIQUE (tenant_id, username), 
	FOREIGN KEY(tenant_id) REFERENCES sys_tenant (id) ON DELETE CASCADE, 
	FOREIGN KEY(dept_id) REFERENCES sys_dept (id) ON DELETE SET NULL
);

CREATE TABLE sys_role_menu (
	role_id INTEGER NOT NULL, 
	menu_id INTEGER NOT NULL, 
	PRIMARY KEY (role_id, menu_id), 
	FOREIGN KEY(role_id) REFERENCES sys_role (id) ON DELETE CASCADE, 
	FOREIGN KEY(menu_id) REFERENCES sys_menu (id) ON DELETE CASCADE
);

CREATE TABLE sys_role_permission (
	role_id INTEGER NOT NULL, 
	permission_id INTEGER NOT NULL, 
	PRIMARY KEY (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES sys_role (id) ON DELETE CASCADE, 
	FOREIGN KEY(permission_id) REFERENCES sys_permission (id) ON DELETE CASCADE
);

CREATE TABLE sys_user_role (
	user_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	PRIMARY KEY (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES sys_user (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES sys_role (id) ON DELETE CASCADE
);

CREATE TABLE sys_login_log (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	user_id INTEGER, 
	username VARCHAR(64) NOT NULL, 
	login_type VARCHAR(16) NOT NULL, 
	status INTEGER NOT NULL, 
	fail_reason VARCHAR(255), 
	ip VARCHAR(64) NOT NULL, 
	ip_region VARCHAR(32), 
	user_agent TEXT, 
	os VARCHAR(64), 
	browser VARCHAR(64), 
	device VARCHAR(32), 
	login_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE sys_operation_log (
	id INTEGER NOT NULL, 
	tenant_id INTEGER NOT NULL, 
	user_id INTEGER, 
	username VARCHAR(64), 
	module VARCHAR(64) NOT NULL, 
	action VARCHAR(32) NOT NULL, 
	action_label VARCHAR(64) NOT NULL, 
	method VARCHAR(8) NOT NULL, 
	path VARCHAR(255) NOT NULL, 
	"query" VARCHAR(512), 
	target VARCHAR(255), 
	params TEXT, 
	status_code INTEGER NOT NULL, 
	success BOOLEAN NOT NULL, 
	error_msg VARCHAR(255), 
	duration_ms INTEGER NOT NULL, 
	ip VARCHAR(64) NOT NULL, 
	ip_region VARCHAR(32), 
	user_agent TEXT, 
	os VARCHAR(64), 
	browser VARCHAR(64), 
	device VARCHAR(32), 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

-- ---------------------------------------------------------------- 复合索引

CREATE INDEX "ix_sys_user_tenant_status" ON "sys_user" ("tenant_id", "status");

CREATE INDEX "ix_sys_role_tenant_status" ON "sys_role" ("tenant_id", "status");

CREATE INDEX "ix_sys_dept_tenant_parent" ON "sys_dept" ("tenant_id", "parent_id");

CREATE INDEX "ix_sys_menu_parent_sort" ON "sys_menu" ("parent_id", "sort");

CREATE INDEX "ix_sys_perm_module_code" ON "sys_permission" ("module", "code");

CREATE INDEX "ix_sys_login_log_tenant_time" ON "sys_login_log" ("tenant_id", "login_at");

CREATE INDEX "ix_sys_login_log_user_time" ON "sys_login_log" ("user_id", "login_at");

CREATE INDEX "ix_sys_oper_log_tenant_time" ON "sys_operation_log" ("tenant_id", "created_at");

CREATE INDEX "ix_sys_oper_log_user_time" ON "sys_operation_log" ("user_id", "created_at");
