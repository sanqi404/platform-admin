-- RBAC 管理平台底座 · 基础数据（POSTGRES）
-- 内容：平台租户、初始管理员、内置角色、权限点字典、菜单树及其授权关系。
-- 初始账号 admin / Admin@123456，首次登录后请立即改密。

-- sys_tenant（1 行）
INSERT INTO "sys_tenant" ("id", "code", "name", "contact", "phone", "status", "max_users", "expire_at", "remark", "created_at", "updated_at") VALUES (1, 'platform', '平台运营中心', '管理员', NULL, 1, 9999, NULL, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
-- sys_permission（23 行）
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (1, 'dashboard:view', '查看工作台', 'dashboard', '工作台', 0, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (2, 'system:user:list', '用户查询', 'user', '用户管理', 1, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (3, 'system:user:create', '用户新增', 'user', '用户管理', 2, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (4, 'system:user:update', '用户编辑', 'user', '用户管理', 3, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (5, 'system:user:delete', '用户删除', 'user', '用户管理', 4, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (6, 'system:user:resetPwd', '重置密码', 'user', '用户管理', 5, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (7, 'system:role:list', '角色查询', 'role', '角色管理', 6, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (8, 'system:role:create', '角色新增', 'role', '角色管理', 7, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (9, 'system:role:update', '角色编辑', 'role', '角色管理', 8, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (10, 'system:role:delete', '角色删除', 'role', '角色管理', 9, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (11, 'system:role:grant', '角色授权', 'role', '角色管理', 10, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (12, 'system:menu:list', '菜单查询', 'menu', '菜单管理', 11, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (13, 'system:menu:create', '菜单新增', 'menu', '菜单管理', 12, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (14, 'system:menu:update', '菜单编辑', 'menu', '菜单管理', 13, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (15, 'system:menu:delete', '菜单删除', 'menu', '菜单管理', 14, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (16, 'system:tenant:list', '租户查询', 'tenant', '租户管理', 15, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (17, 'system:tenant:create', '租户新增', 'tenant', '租户管理', 16, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (18, 'system:tenant:update', '租户编辑', 'tenant', '租户管理', 17, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (19, 'system:tenant:delete', '租户删除', 'tenant', '租户管理', 18, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (20, 'system:loginlog:list', '登录日志查询', 'loginlog', '日志审计', 19, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (21, 'system:loginlog:delete', '登录日志清理', 'loginlog', '日志审计', 20, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (22, 'system:operlog:list', '操作日志查询', 'operlog', '日志审计', 21, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_permission" ("id", "code", "name", "module", "group", "sort", "remark", "created_at", "updated_at") VALUES (23, 'system:operlog:delete', '操作日志清理', 'operlog', '日志审计', 22, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
-- sys_menu（24 行）
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (1, 0, '工作台', 'Dashboard', '/dashboard', 'dashboard/index', 'Odometer', 'menu', 'dashboard:view', 0, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (2, 0, '系统管理', 'System', '/system', '', 'Setting', 'dir', NULL, 10, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (3, 2, '用户管理', 'System.SystemUser', '/system/user', 'system/user/index', 'User', 'menu', 'system:user:list', 0, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (4, 3, '新增用户', 'System.SystemUser.SystemUserCreate', '', '', NULL, 'button', 'system:user:create', 0, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (5, 3, '编辑用户', 'System.SystemUser.SystemUserUpdate', '', '', NULL, 'button', 'system:user:update', 10, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (6, 3, '删除用户', 'System.SystemUser.SystemUserDelete', '', '', NULL, 'button', 'system:user:delete', 20, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (7, 3, '重置密码', 'System.SystemUser.SystemUserResetPwd', '', '', NULL, 'button', 'system:user:resetPwd', 30, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (8, 2, '角色权限', 'System.SystemRole', '/system/role', 'system/role/index', 'UserFilled', 'menu', 'system:role:list', 10, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (9, 8, '新增角色', 'System.SystemRole.SystemRoleCreate', '', '', NULL, 'button', 'system:role:create', 0, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (10, 8, '编辑角色', 'System.SystemRole.SystemRoleUpdate', '', '', NULL, 'button', 'system:role:update', 10, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (11, 8, '删除角色', 'System.SystemRole.SystemRoleDelete', '', '', NULL, 'button', 'system:role:delete', 20, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (12, 8, '分配权限', 'System.SystemRole.SystemRoleGrant', '', '', NULL, 'button', 'system:role:grant', 30, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (13, 2, '菜单管理', 'System.SystemMenu', '/system/menu', 'system/menu/index', 'Menu', 'menu', 'system:menu:list', 20, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (14, 13, '新增菜单', 'System.SystemMenu.SystemMenuCreate', '', '', NULL, 'button', 'system:menu:create', 0, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (15, 13, '编辑菜单', 'System.SystemMenu.SystemMenuUpdate', '', '', NULL, 'button', 'system:menu:update', 10, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (16, 13, '删除菜单', 'System.SystemMenu.SystemMenuDelete', '', '', NULL, 'button', 'system:menu:delete', 20, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (17, 2, '租户管理', 'System.SystemTenant', '/system/tenant', 'system/tenant/index', 'OfficeBuilding', 'menu', 'system:tenant:list', 30, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (18, 17, '新增租户', 'System.SystemTenant.SystemTenantCreate', '', '', NULL, 'button', 'system:tenant:create', 0, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (19, 17, '编辑租户', 'System.SystemTenant.SystemTenantUpdate', '', '', NULL, 'button', 'system:tenant:update', 10, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (20, 17, '删除租户', 'System.SystemTenant.SystemTenantDelete', '', '', NULL, 'button', 'system:tenant:delete', 20, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (21, 2, '登录日志', 'System.SystemLoginLog', '/system/login-log', 'system/login-log/index', 'Tickets', 'menu', 'system:loginlog:list', 40, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (22, 21, '清理登录日志', 'System.SystemLoginLog.SystemLoginLogDelete', '', '', NULL, 'button', 'system:loginlog:delete', 0, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (23, 2, '操作日志', 'System.SystemOperLog', '/system/operation-log', 'system/operation-log/index', 'Document', 'menu', 'system:operlog:list', 50, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_menu" ("id", "parent_id", "title", "name", "path", "component", "icon", "type", "perm_code", "sort", "visible", "keep_alive", "is_ext", "status", "created_at", "updated_at") VALUES (24, 23, '清理操作日志', 'System.SystemOperLog.SystemOperLogDelete', '', '', NULL, 'button', 'system:operlog:delete', 0, 1, 0, 0, 1, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
-- sys_role（2 行）
INSERT INTO "sys_role" ("id", "tenant_id", "code", "name", "data_scope", "custom_dept_ids", "status", "is_system", "sort", "remark", "created_at", "updated_at") VALUES (1, 1, 'super_admin', '超级管理员', 1, '[]', 1, 1, 1, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
INSERT INTO "sys_role" ("id", "tenant_id", "code", "name", "data_scope", "custom_dept_ids", "status", "is_system", "sort", "remark", "created_at", "updated_at") VALUES (2, 1, 'viewer', '只读观察员', 1, '[]', 1, 1, 2, '仅可查看，用于演示权限差异', '2026-11-26 05:36:56', '2026-11-26 05:36:56');
-- sys_user（1 行）
INSERT INTO "sys_user" ("id", "tenant_id", "dept_id", "username", "nickname", "password_hash", "email", "phone", "avatar", "status", "is_superuser", "login_fail_count", "locked_until", "last_login_at", "last_login_ip", "created_at", "updated_at") VALUES (1, 1, NULL, 'admin', '平台管理员', '$2b$12$nM7RVM6iR8O0JWNWnFmL0u3cpar4a/dmpzafraLDsR0B8hXCoRfpC', NULL, NULL, NULL, 1, 1, 0, NULL, NULL, NULL, '2026-11-26 05:36:56', '2026-11-26 05:36:56');
-- sys_role_menu（27 行）
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 1);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 2);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 3);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 4);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 5);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 6);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 7);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 8);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 9);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 10);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 11);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 12);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 13);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 14);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 15);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 16);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 17);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 18);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 19);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 20);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 21);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 22);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 23);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (1, 24);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (2, 1);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (2, 2);
INSERT INTO "sys_role_menu" ("role_id", "menu_id") VALUES (2, 3);
-- sys_role_permission（25 行）
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 1);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 2);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 3);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 4);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 5);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 6);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 7);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 8);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 9);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 10);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 11);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 12);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 13);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 14);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 15);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 16);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 17);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 18);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 19);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 20);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 21);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 22);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (1, 23);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (2, 1);
INSERT INTO "sys_role_permission" ("role_id", "permission_id") VALUES (2, 2);
-- sys_user_role（1 行）
INSERT INTO "sys_user_role" ("user_id", "role_id") VALUES (1, 1);
