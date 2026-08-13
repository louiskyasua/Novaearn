@app.route(
    "/admin/update-withdrawal/<int:withdrawal_id>/<action>",
    methods=["POST"],
)
@admin_required
def admin_update_withdrawal(withdrawal_id, action):
    if action not in {"approve", "reject"}:
        flash("Invalid withdrawal action.")
        return redirect(url_for("admin"))

    c = db()

    try:
        wd = c.execute(
            """
            SELECT *
            FROM withdrawals
            WHERE id=?
            """,
            (withdrawal_id,),
        ).fetchone()

        if not wd:
            c.rollback()
            flash("Withdrawal not found.")
            return redirect(url_for("admin"))

        if wd["status"] != "pending":
            c.rollback()
            flash("Withdrawal is no longer pending.")
            return redirect(url_for("admin"))

        new_status = (
            "approved"
            if action == "approve"
            else "rejected"
        )

        # IMPORTANT:
        # Only one request is allowed to transition the withdrawal
        # from pending to its final state.
        result = c.execute(
            """
            UPDATE withdrawals
            SET status=?
            WHERE id=?
            AND status='pending'
            """,
            (
                new_status,
                withdrawal_id,
            ),
        )

        # If another admin request already processed it,
        # DO NOT change the balance again.
        if result.rowcount != 1:
            c.rollback()
            flash("Withdrawal was already processed.")
            return redirect(url_for("admin"))

        now = datetime.now().isoformat()

        if action == "reject":
            # The money was reserved when the withdrawal
            # was submitted, so return it to the user.
            refund = c.execute(
                """
                UPDATE users
                SET balance=balance+?
                WHERE id=?
                """,
                (
                    wd["amount"],
                    wd["user_id"],
                ),
            )

            if refund.rowcount != 1:
                raise RuntimeError(
                    "User balance could not be refunded."
                )

            c.execute(
                """
                INSERT INTO transactions(
                    user_id,
                    kind,
                    amount,
                    note,
                    created_at
                )
                VALUES(?,?,?,?,?)
                """,
                (
                    wd["user_id"],
                    "WITHDRAWAL_REFUNDED",
                    wd["amount"],
                    "Withdrawal rejected and balance refunded",
                    now,
                ),
            )

        else:
            # IMPORTANT:
            # The balance was already deducted when the request
            # was created. Approval must NOT deduct it again.
            c.execute(
                """
                INSERT INTO transactions(
                    user_id,
                    kind,
                    amount,
                    note,
                    created_at
                )
                VALUES(?,?,?,?,?)
                """,
                (
                    wd["user_id"],
                    "WITHDRAWAL_APPROVED",
                    0,
                    "Withdrawal approved by admin",
                    now,
                ),
            )

        c.commit()

    except Exception:
        c.rollback()
        flash("Unable to update withdrawal.")
        return redirect(url_for("admin"))

    finally:
        c.close()

    if action == "approve":
        flash("Withdrawal approved.")
    else:
        flash("Withdrawal rejected and balance refunded.")

    return redirect(url_for("admin"))
