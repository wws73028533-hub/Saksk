# -*- coding: utf-8 -*-
"""用户端弹窗 API

接口：
- GET  /api/popups/active               获取当前用户应显示的活跃弹窗列表（支持轮播）
- POST /api/popups/<id>/dismiss         关闭弹窗（记录到 popup_dismissals）
- POST /api/popups/<id>/view           记录弹窗显示（用于统计）
"""

from flask import Blueprint, jsonify, session, request, current_app
from app.core.extensions import limiter
from app.modules.popups.services.popup_service import PopupService

popups_api_bp = Blueprint('popups_api', __name__)


@popups_api_bp.route('/popups/active')
@limiter.exempt
def api_popups_active():
    """获取当前用户应显示的活跃弹窗列表"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    user_id = int(session.get('user_id'))
    limit = int(request.args.get('limit', 10))
    limit = max(1, min(limit, 50))  # 限制在1-50之间
    
    try:
        popups = PopupService.get_active_popups_for_user(user_id, limit)
        return jsonify({
            'status': 'success',
            'data': popups,
            'count': len(popups)
        })
    except Exception as e:
        current_app.logger.error(f'获取活跃弹窗失败: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '获取弹窗列表失败'
        }), 500


@popups_api_bp.route('/popups/<int:popup_id>/dismiss', methods=['POST'])
@limiter.exempt
def api_popup_dismiss(popup_id: int):
    """关闭弹窗（不再提示）"""
    if not session.get('user_id'):
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401
    
    user_id = int(session.get('user_id'))
    
    try:
        success = PopupService.dismiss_popup(popup_id, user_id)
        if success:
            return jsonify({
                'status': 'success',
                'message': '弹窗已关闭'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '关闭弹窗失败'
            }), 500
    except Exception as e:
        current_app.logger.error(f'关闭弹窗失败: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': '关闭弹窗失败'
        }), 500


@popups_api_bp.route('/popups/<int:popup_id>/view', methods=['POST'])
@limiter.exempt
def api_popup_view(popup_id: int):
    """记录弹窗显示（用于统计）"""
    user_id = None
    if session.get('user_id'):
        user_id = int(session.get('user_id'))
    
    try:
        PopupService.record_popup_view(popup_id, user_id)
        return jsonify({
            'status': 'success',
            'message': '已记录显示'
        })
    except Exception as e:
        current_app.logger.error(f'记录弹窗显示失败: {str(e)}', exc_info=True)
        # 记录失败不影响主流程，返回成功
        return jsonify({
            'status': 'success',
            'message': '已记录显示'
        })


