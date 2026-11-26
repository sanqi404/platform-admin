import type { Directive, DirectiveBinding } from 'vue'
import { useUserStore } from '@/stores/user'

type Value = string | string[]

/**
 * v-perm="'system:user:create'"        无权限 -> 从 DOM 移除（等价 v-if，推荐用于新增/删除按钮）
 * v-perm:show="'system:user:update'"   无权限 -> display:none（等价 v-show，保留节点，适合频繁切换）
 * 数组语义为「任一命中」；需要全部命中用 v-perm:all 或 v-perm:all:show
 */
function resolve(binding: DirectiveBinding<Value>): { visible: boolean; useShow: boolean } {
  const user = useUserStore()
  const value = binding.value
  const codes = Array.isArray(value) ? value : [value]
  const needAll = binding.modifiers.all === true
  const useShow = binding.arg === 'show' || binding.modifiers.show === true

  const matched = needAll
    ? codes.every((c) => user.hasPerm(c))
    : codes.some((c) => user.hasPerm(c))

  return { visible: matched && codes.length > 0, useShow }
}

function apply(el: HTMLElement, binding: DirectiveBinding<Value>): void {
  const { visible, useShow } = resolve(binding)
  // 记录原始 display，便于权限变化后恢复
  const flag = '__permHidden'
  const cache = el as HTMLElement & { [key: string]: unknown }

  if (visible) {
    if (cache[flag]) {
      el.style.display = (cache.__permDisplay as string) || ''
      cache[flag] = false
    }
    return
  }

  if (!cache[flag]) {
    cache.__permDisplay = el.style.display || ''
    cache[flag] = true
  }

  if (useShow) {
    el.style.display = 'none'
  } else if (el.parentNode) {
    el.parentNode.removeChild(el)
  }
}

export const vPerm: Directive<HTMLElement, Value> = {
  mounted: apply,
  updated: apply,
}

/** v-role="['super_admin']" / v-role:show="'viewer'" */
export const vRole: Directive<HTMLElement, Value> = {
  mounted(el, binding) {
    const user = useUserStore()
    const value = binding.value
    const roles = Array.isArray(value) ? value : [value]
    if (user.hasRole(roles)) return
    if (binding.arg === 'show' || binding.modifiers.show) {
      el.style.display = 'none'
    } else if (el.parentNode) {
      el.parentNode.removeChild(el)
    }
  },
}

export function setupDirectives(app: { directive: (name: string, d: Directive) => void }): void {
  app.directive('perm', vPerm)
  app.directive('role', vRole)
}
