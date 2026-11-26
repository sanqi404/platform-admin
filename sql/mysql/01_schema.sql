-- RBAC 管理平台底座 · 初始化脚本（MYSQL）
-- 由 ORM 模型与种子数据导出，与 backend/alembic 迁移保持一致。
-- 用法：mysql -u root -p < 01_schema.sql，再执行 02_seed.sql


SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `rbac` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `rbac`;


-- ---------------------------------------------------------------- 表结构

CREATE TABLE sys_tenant (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	code VARCHAR(64) NOT NULL COMMENT '租户编码', 
	name VARCHAR(128) NOT NULL COMMENT '租户名称', 
	contact VARCHAR(64), 
	phone VARCHAR(32), 
	status INTEGER NOT NULL COMMENT '1启用 0停用', 
	max_users INTEGER NOT NULL, 
	expire_at DATETIME, 
	remark VARCHAR(255), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_permission (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	code VARCHAR(128) NOT NULL COMMENT '权限码 模块:资源:动作', 
	name VARCHAR(64) NOT NULL, 
	module VARCHAR(64) NOT NULL COMMENT '所属模块', 
	`group` VARCHAR(64) NOT NULL COMMENT 'UI 分组', 
	sort INTEGER NOT NULL, 
	remark VARCHAR(255), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_menu (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	parent_id BIGINT NOT NULL, 
	title VARCHAR(64) NOT NULL COMMENT '菜单标题', 
	name VARCHAR(64) NOT NULL COMMENT '路由 name，唯一', 
	path VARCHAR(128) NOT NULL COMMENT '路由 path', 
	component VARCHAR(128) NOT NULL COMMENT '组件路径，如 system/user/index', 
	icon VARCHAR(64), 
	type VARCHAR(16) NOT NULL COMMENT 'dir 目录 / menu 菜单 / button 按钮', 
	perm_code VARCHAR(128) COMMENT '绑定权限码', 
	sort INTEGER NOT NULL, 
	visible BOOL NOT NULL COMMENT '是否在侧边栏显示', 
	keep_alive BOOL NOT NULL, 
	is_ext BOOL NOT NULL COMMENT '是否外链', 
	status INTEGER NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_dept (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	tenant_id BIGINT NOT NULL, 
	parent_id BIGINT NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	leader VARCHAR(64), 
	sort INTEGER NOT NULL, 
	status INTEGER NOT NULL, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_dept_tenant_name UNIQUE (tenant_id, name, parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_role (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	tenant_id BIGINT NOT NULL, 
	code VARCHAR(64) NOT NULL COMMENT '角色标识，前端 v-role 使用', 
	name VARCHAR(64) NOT NULL, 
	data_scope INTEGER NOT NULL COMMENT '1全部 2本部门 3本部及以下 4仅本人 5自定义', 
	custom_dept_ids JSON NOT NULL, 
	status INTEGER NOT NULL, 
	is_system BOOL NOT NULL COMMENT '内置角色不可删除', 
	is_all_perm TINYINT(1) NOT NULL DEFAULT 0 COMMENT '全量权限：忽略绑定直接拥有全部权限点与菜单', 
	sort INTEGER NOT NULL, 
	remark VARCHAR(255), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_role_tenant_code UNIQUE (tenant_id, code), 
	FOREIGN KEY(tenant_id) REFERENCES sys_tenant (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_user (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	tenant_id BIGINT NOT NULL, 
	dept_id BIGINT, 
	username VARCHAR(64) NOT NULL, 
	nickname VARCHAR(64) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	email VARCHAR(128), 
	phone VARCHAR(32), 
	avatar VARCHAR(255), 
	status INTEGER NOT NULL COMMENT '1启用 0停用', 
	is_superuser BOOL NOT NULL COMMENT '超管绕过权限校验', 
	login_fail_count INTEGER NOT NULL, 
	locked_until DATETIME, 
	last_login_at DATETIME, 
	last_login_ip VARCHAR(64), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_tenant_username UNIQUE (tenant_id, username), 
	FOREIGN KEY(tenant_id) REFERENCES sys_tenant (id) ON DELETE CASCADE, 
	FOREIGN KEY(dept_id) REFERENCES sys_dept (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_role_menu (
	role_id BIGINT NOT NULL, 
	menu_id BIGINT NOT NULL, 
	PRIMARY KEY (role_id, menu_id), 
	FOREIGN KEY(role_id) REFERENCES sys_role (id) ON DELETE CASCADE, 
	FOREIGN KEY(menu_id) REFERENCES sys_menu (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_role_permission (
	role_id BIGINT NOT NULL, 
	permission_id BIGINT NOT NULL, 
	PRIMARY KEY (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES sys_role (id) ON DELETE CASCADE, 
	FOREIGN KEY(permission_id) REFERENCES sys_permission (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_user_role (
	user_id BIGINT NOT NULL, 
	role_id BIGINT NOT NULL, 
	PRIMARY KEY (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES sys_user (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES sys_role (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_login_log (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	tenant_id BIGINT NOT NULL, 
	user_id BIGINT COMMENT '登录成功/失败已识别用户时写入，用户不存在则空', 
	username VARCHAR(64) NOT NULL COMMENT '提交的登录账号', 
	login_type VARCHAR(16) NOT NULL COMMENT 'login 登录 / logout 登出 / refresh 刷新令牌', 
	status INTEGER NOT NULL COMMENT '1成功 0失败', 
	fail_reason VARCHAR(255), 
	ip VARCHAR(64) NOT NULL, 
	ip_region VARCHAR(32) COMMENT '本机/内网/公网', 
	user_agent TEXT, 
	os VARCHAR(64), 
	browser VARCHAR(64), 
	device VARCHAR(32) COMMENT 'PC/移动端/程序调用', 
	login_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE sys_operation_log (
	id BIGINT NOT NULL AUTO_INCREMENT, 
	tenant_id BIGINT NOT NULL, 
	user_id BIGINT, 
	username VARCHAR(64), 
	module VARCHAR(64) NOT NULL COMMENT '业务模块', 
	action VARCHAR(32) NOT NULL COMMENT 'create/update/delete/grant/export/reset_password/other', 
	action_label VARCHAR(64) NOT NULL COMMENT '人可读动作，如「新增用户管理」', 
	method VARCHAR(8) NOT NULL, 
	path VARCHAR(255) NOT NULL, 
	query VARCHAR(512) COMMENT '查询串', 
	target VARCHAR(255) COMMENT '操作对象，如 users #3', 
	params TEXT COMMENT '请求体，已脱敏截断', 
	status_code INTEGER NOT NULL, 
	success BOOL NOT NULL, 
	error_msg VARCHAR(255), 
	duration_ms INTEGER NOT NULL, 
	ip VARCHAR(64) NOT NULL, 
	ip_region VARCHAR(32), 
	user_agent TEXT, 
	os VARCHAR(64), 
	browser VARCHAR(64), 
	device VARCHAR(32), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ---------------------------------------------------------------- 复合索引

CREATE INDEX `ix_sys_user_tenant_status` ON `sys_user` (`tenant_id`, `status`);

CREATE INDEX `ix_sys_role_tenant_status` ON `sys_role` (`tenant_id`, `status`);

CREATE INDEX `ix_sys_dept_tenant_parent` ON `sys_dept` (`tenant_id`, `parent_id`);

CREATE INDEX `ix_sys_menu_parent_sort` ON `sys_menu` (`parent_id`, `sort`);

CREATE INDEX `ix_sys_perm_module_code` ON `sys_permission` (`module`, `code`);

CREATE INDEX `ix_sys_login_log_tenant_time` ON `sys_login_log` (`tenant_id`, `login_at`);

CREATE INDEX `ix_sys_login_log_user_time` ON `sys_login_log` (`user_id`, `login_at`);

CREATE INDEX `ix_sys_oper_log_tenant_time` ON `sys_operation_log` (`tenant_id`, `created_at`);

CREATE INDEX `ix_sys_oper_log_user_time` ON `sys_operation_log` (`user_id`, `created_at`);

SET FOREIGN_KEY_CHECKS = 1;
