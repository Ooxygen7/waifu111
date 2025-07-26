from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
)
from web.factory import get_config

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """登录页面"""
    if "logged_in" in session:
        if session.get("user_role") == "admin":
            return redirect(url_for("admin.index"))
        elif session.get("user_role") == "viewer":
            return redirect(url_for("viewer.viewer_index"))
        else:
            # 清除无效的session
            session.pop("logged_in", None)
            session.pop("user_role", None)

    error = None
    if request.method == "POST":
        password = request.form.get("password")
        config = get_config()

        if password == config["WEB_PW"]:
            session["logged_in"] = True
            session["user_role"] = "admin"
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("admin.index"))
        elif password == config["VIEWER_PW"]:
            session["logged_in"] = True
            session["user_role"] = "viewer"
            return redirect(url_for("viewer.viewer_index"))
        else:
            error = "密码错误"

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    """登出"""
    session.pop("logged_in", None)
    session.pop("user_role", None)
    return redirect(url_for("auth.login"))