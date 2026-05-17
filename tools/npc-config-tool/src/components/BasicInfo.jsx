// 基本信息面板
// 配置 NPC 的基础属性
import React from 'react'
import { User, Image } from 'lucide-react'

// =========================================
// AnimationRow - 内部动画行组件
// 复用单个方向的帧范围输入
// =========================================
function AnimationRow({ animKey, label, value, onChange }) {
  // value: [start, end] 帧范围数组
  const start = value ? value[0] : 0
  const end = value ? value[1] : 1

  return (
    <div className="flex items-center gap-3 bg-slate-700/50 p-2.5 rounded-lg">
      <span className="text-xs text-slate-300 w-24 font-mono">{animKey}:</span>
      <input
        type="number"
        value={start}
        onChange={(e) => onChange(animKey, [parseInt(e.target.value) || 0, end])}
        className="w-16 px-2 py-1 rounded text-center bg-slate-600 border border-slate-500 text-slate-200 text-sm"
        min="0"
      />
      <span className="text-slate-500">~</span>
      <input
        type="number"
        value={end}
        onChange={(e) => onChange(animKey, [start, parseInt(e.target.value) || 1])}
        className="w-16 px-2 py-1 rounded text-center bg-slate-600 border border-slate-500 text-slate-200 text-sm"
        min="0"
      />
      <span className="text-xs text-slate-500 ml-auto">{label}</span>
    </div>
  )
}

/** 四个方向 */
const DIRECTIONS = ['down', 'left', 'right', 'up']

/** 方向中文标签 */
const DIRECTION_LABELS = {
  down: '向下', left: '向左', right: '向右', up: '向上'
}

// 定义组件 BasicInfo
export default function BasicInfo({ config, onChange }) {
  // config → 父组件传来的 NPC 配置数据 (v2 格式)
  // onChange → 父组件传来的回调函数，调用它可以通知父组件修改数据

  // v2 字段读取辅助函数
  const update = (key, value) => onChange(key, value)

  // 更新 meta 下的字段
  const updateMeta = (key, value) => onChange('meta', { ...(config.meta || {}), [key]: value })

  // 更新 presentation 下的字段
  const updatePresentation = (key, value) => onChange('presentation', { ...(config.presentation || {}), [key]: value })

  // 更新 render_cfg 下的字段
  const updateRenderCfg = (key, value) => {
    const current = config.presentation?.render_cfg || {}
    onChange('presentation', {
      ...(config.presentation || {}),
      render_cfg: { ...current, [key]: value }
    })
  }

  // 更新 render_cfg.animations 下的字段
  const updateAnim = (key, value) => {
    const current = config.presentation?.render_cfg?.animations || {}
    const newAnims = { ...current, [key]: value }
    updateRenderCfg('animations', newAnims)
  }

  // JSX 界面渲染
  return (
    <div className="space-y-6 max-w-2xl">
      {/*标题区域 */}
      <h2 className="text-lg font-semibold flex items-center gap-2">
        <User className="w-5 h-5 text-blue-500" />
        基本信息
      </h2>
      {/*内容区域 */}
      <div className="grid gap-6">
        {/* NPC ID-自动生成且不能修改 */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            NPC ID <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={config.id || ''}
            onChange={(e) => update('id', e.target.value)}
            placeholder="如: village_chief_001"
            className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
            disabled={!!config.id}
          />
          <p className="mt-1 text-xs text-slate-500">
            唯一标识符，用于 WebSocket 连接和 API 调用
          </p>
        </div>
        {/* NPC 名称 - v2: meta.name */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            名称
          </label>
          <input
            type="text"
            value={config.meta?.name || ''}
            onChange={(e) => updateMeta('name', e.target.value)}
            placeholder="如: 老村长"
            className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
          />
        </div>
        {/* NPC 身份描述 - v2: persona.identity */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            身份描述
          </label>
          <textarea
            value={config.persona?.identity || ''}
            onChange={(e) => update('persona', { ...(config.persona || {}), identity: e.target.value })}
            placeholder="如：一个慈祥的老者，在这个村庄生活了五十年，深受村民尊敬..."
            rows={3}
            className="w-full px-4 py-2 rounded-lg resize-none bg-slate-700 border border-slate-600"
          />
        </div>
        {/* NPC 精灵图路径 - v2: presentation.sprite */}
        <div>
          <label className="block text-sm font-medium text-slate-400 mb-2">
            <Image className="w-4 h-4 inline mr-1" />
            精灵图
          </label>
          <input
            type="text"
            value={config.presentation?.sprite || ''}
            onChange={(e) => updatePresentation('sprite', e.target.value)}
            placeholder="如: /mygame/assets/npc/merchant.png"
            className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
          />
          <p className="mt-1 text-xs text-slate-500">
            游戏资源中对应的精灵图路径（建议使用 / 路径分隔符）
          </p>
        </div>
        {/* 精灵图渲染配置 - v2: presentation.render_cfg */}
        <div className="border-t border-slate-700 pt-6">
          <h3 className="text-sm font-medium text-slate-300 mb-4 flex items-center gap-2">
            <Image className="w-4 h-4" />
            精灵图渲染配置
          </h3>
          <div className="grid grid-cols-3 gap-4">
            {/* 帧宽度 */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                帧宽度
              </label>
              <input
                type="number"
                value={config.presentation?.render_cfg?.frameWidth || ''}
                onChange={(e) => updateRenderCfg('frameWidth', e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="如: 48"
                className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
                min="1"
              />
            </div>
            {/* 帧高度 */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                帧高度
              </label>
              <input
                type="number"
                value={config.presentation?.render_cfg?.frameHeight || ''}
                onChange={(e) => updateRenderCfg('frameHeight', e.target.value ? parseInt(e.target.value) : undefined)}
                placeholder="如: 64"
                className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
                min="1"
              />
            </div>
            {/* 缩放 */}
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-2">
                缩放
              </label>
              <input
                type="number"
                value={config.presentation?.render_cfg?.scale || 2}
                onChange={(e) => updateRenderCfg('scale', e.target.value ? parseInt(e.target.value) : 2)}
                placeholder="如: 2"
                className="w-full px-4 py-2 rounded-lg bg-slate-700 border border-slate-600"
                min="1"
                max="10"
              />
            </div>
          </div>
          {/* 动画配置 - v2: presentation.render_cfg.animations */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-slate-400 mb-2">
              动画帧配置
            </label>

            {/* Idle 动画（站立） */}
            <details className="mb-3" open>
              <summary className="cursor-pointer text-sm font-medium text-slate-300 mb-3 hover:text-slate-200 transition-colors">
                🧍 Idle 站立动画
              </summary>
              <div className="space-y-2 mt-2">
                {DIRECTIONS.map(dir => {
                  const animKey = `idle_${dir}`
                  const anims = config.presentation?.render_cfg?.animations || {}
                  const defaultValue = anims.idle_down ? [anims.idle_down[0], anims.idle_down[1]] : [0, 1]
                  return (
                    <AnimationRow
                      key={animKey}
                      animKey={animKey}
                      label={DIRECTION_LABELS[dir]}
                      value={anims[animKey] || defaultValue}
                      onChange={updateAnim}
                    />
                  )
                })}
              </div>
            </details>

            {/* Walk 动画（行走） */}
            <details className="mb-3" open>
              <summary className="cursor-pointer text-sm font-medium text-slate-300 mb-3 hover:text-slate-200 transition-colors">
                🚶 Walk 行走动画
              </summary>
              <div className="space-y-2 mt-2">
                {DIRECTIONS.map(dir => {
                  const animKey = `walk_${dir}`
                  const anims = config.presentation?.render_cfg?.animations || {}
                  const defaultValue = anims.walk_down ? [anims.walk_down[0], anims.walk_down[1]] : [8, 12]
                  return (
                    <AnimationRow
                      key={animKey}
                      animKey={animKey}
                      label={DIRECTION_LABELS[dir]}
                      value={anims[animKey] || defaultValue}
                      onChange={updateAnim}
                    />
                  )
                })}
              </div>
            </details>

            <p className="mt-2 text-xs text-slate-500">
              设置精灵图的帧尺寸和动画帧范围（idle_*/walk_* 覆盖 down/left/right/up 四个方向）；
              缺失的方向将由引擎自动回退（如 left 缺→镜像 right，up 缺→复用 down）
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
