import maya
from flask import Blueprint, session, flash, render_template, request, url_for, redirect
from flask_security import login_required, current_user
from topicdb.core.models.association import Association
from topicdb.core.models.collaborationmode import CollaborationMode
from topicdb.core.store.retrievalmode import RetrievalMode
from werkzeug.exceptions import abort

from contextualise.topic_store import get_topic_store

bp = Blueprint("association", __name__)

UNIVERSAL_SCOPE = "*"


@bp.route("/associations/<map_identifier>/<topic_identifier>")
@login_required
def index(map_identifier, topic_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    associations = topic_store.get_topic_associations(map_identifier, topic_identifier)

    # occurrences_stats = topic_store.get_topic_occurrences_statistics(map_identifier, topic_identifier)

    creation_date_attribute = topic.get_attribute_by_name("creation-timestamp")
    creation_date = maya.parse(creation_date_attribute.value) if creation_date_attribute else "Undefined"

    return render_template(
        "association/index.html",
        topic_map=topic_map,
        topic=topic,
        associations=associations,
        creation_date=creation_date,
    )


@bp.route("/associations/create/<map_identifier>/<topic_identifier>", methods=("GET", "POST"))
@login_required
def create(map_identifier, topic_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    error = 0

    if request.method == "POST":
        form_association_dest_topic_ref = request.form["association-dest-topic-ref"].strip()
        form_association_dest_role_spec = request.form["association-dest-role-spec"].strip()
        form_association_src_topic_ref = topic_identifier
        form_association_src_role_spec = request.form["association-src-role-spec"].strip()
        form_association_instance_of = request.form["association-instance-of"].strip()
        form_association_scope = request.form["association-scope"].strip()
        form_association_name = request.form["association-name"].strip()
        form_association_identifier = request.form["association-identifier"].strip()

        # If no values have been provided set their default values
        if not form_association_dest_role_spec:
            form_association_dest_role_spec = "related"
        if not form_association_src_role_spec:
            form_association_src_role_spec = "related"
        if not form_association_instance_of:
            form_association_instance_of = "association"
        if not form_association_scope:
            form_association_scope = session["current_scope"]
        if not form_association_name:
            form_association_name = "Undefined"

        # Validate form inputs
        if not topic_store.topic_exists(topic_map.identifier, form_association_dest_topic_ref):
            error = error | 1
        if form_association_dest_role_spec != "related" and not topic_store.topic_exists(
            topic_map.identifier, form_association_dest_role_spec
        ):
            error = error | 2
        if form_association_src_role_spec != "related" and not topic_store.topic_exists(
            topic_map.identifier, form_association_src_role_spec
        ):
            error = error | 4
        if form_association_instance_of != "association" and not topic_store.topic_exists(
            topic_map.identifier, form_association_instance_of
        ):
            error = error | 8
        if form_association_scope != UNIVERSAL_SCOPE and not topic_store.topic_exists(
            topic_map.identifier, form_association_scope
        ):
            error = error | 16
        if form_association_identifier and topic_store.topic_exists(topic_map.identifier, form_association_identifier):
            error = error | 32

        # If role identifier topics are missing then create them
        if error & 2:  # Destination role spec
            pass
        if error & 4:  # Source role spec
            pass

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            association = Association(
                identifier=form_association_identifier,
                instance_of=form_association_instance_of,
                name=form_association_name,
                scope=form_association_scope,
                src_topic_ref=form_association_src_topic_ref,
                dest_topic_ref=form_association_dest_topic_ref,
                src_role_spec=form_association_src_role_spec,
                dest_role_spec=form_association_dest_role_spec,
            )

            # Persist association object to the topic store
            topic_store.set_association(map_identifier, association)

            flash("Association successfully created.", "success")
            return redirect(
                url_for("association.index", map_identifier=topic_map.identifier, topic_identifier=topic_identifier,)
            )

        return render_template(
            "association/create.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            association_instance_of=form_association_instance_of,
            association_src_topic_ref=form_association_src_topic_ref,
            association_src_role_spec=form_association_src_role_spec,
            association_dest_topic_ref=form_association_dest_topic_ref,
            association_dest_role_spec=form_association_dest_role_spec,
            association_scope=form_association_scope,
            association_name=form_association_name,
            association_identifier=form_association_identifier,
        )

    return render_template("association/create.html", error=error, topic_map=topic_map, topic=topic,)


@bp.route(
    "/associations/delete/<map_identifier>/<topic_identifier>/<association_identifier>", methods=("GET", "POST"),
)
@login_required
def delete(map_identifier, topic_identifier, association_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    association = topic_store.get_association(map_identifier, association_identifier)

    if request.method == "POST":
        topic_store.delete_association(map_identifier, association_identifier)
        flash("Association successfully deleted.", "warning")
        return redirect(
            url_for("association.index", map_identifier=topic_map.identifier, topic_identifier=topic.identifier,)
        )

    return render_template("association/delete.html", topic_map=topic_map, topic=topic, association=association,)


@bp.route("/associations/view/<map_identifier>/<topic_identifier>/<association_identifier>")
@login_required
def view(map_identifier, topic_identifier, association_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    association = topic_store.get_association(map_identifier, association_identifier)

    return render_template("association/view.html", topic_map=topic_map, topic=topic, association=association,)


@bp.route(
    "/associations/view-member/<map_identifier>/<topic_identifier>/<association_identifier>/<member_identifier>",
    methods=("GET", "POST"),
)
@login_required
def view_member(map_identifier, topic_identifier, association_identifier, member_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    association = topic_store.get_association(map_identifier, association_identifier)
    member = association.get_member(member_identifier)

    return render_template(
        "association/view_member.html", topic_map=topic_map, topic=topic, association=association, member=member,
    )


@bp.route(
    "/associations/add-member/<map_identifier>/<topic_identifier>/<association_identifier>", methods=("GET", "POST"),
)
@login_required
def add_member(map_identifier, topic_identifier, association_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    association = topic_store.get_association(map_identifier, association_identifier)
    if association is None:
        abort(404)

    error = 0

    if request.method == "POST":
        form_role_spec = request.form["role-spec"].strip()
        form_topic_reference = request.form["topic-reference"].strip()

        # Validate form inputs
        if not form_role_spec:
            error = error | 1
        if not topic_store.topic_exists(topic_map.identifier, form_role_spec):
            error = error | 2
        if not form_topic_reference:
            error = error | 4
        if not topic_store.topic_exists(topic_map.identifier, form_topic_reference):
            error = error | 8

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            association.create_member(form_topic_reference, form_role_spec)
            topic_store.delete_association(map_identifier, association_identifier)
            topic_store.set_association(map_identifier, association)

            flash("Member successfully added.", "success")
            return redirect(
                url_for(
                    "association.view",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                    association_identifier=association_identifier,
                )
            )

        return render_template(
            "association/add_member.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            association=association,
            role_spec=form_role_spec,
            topic_reference=form_topic_reference,
        )

    return render_template(
        "association/add_member.html", error=error, topic_map=topic_map, topic=topic, association=association,
    )


@bp.route(
    "/associations/delete-member/<map_identifier>/<topic_identifier>/<association_identifier>/<member_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete_member(map_identifier, topic_identifier, association_identifier, member_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    association = topic_store.get_association(map_identifier, association_identifier)
    if association is None:
        abort(404)

    member = association.get_member(member_identifier)

    if request.method == "POST":
        if len(association.members) > 2:
            association.remove_member(member_identifier)
            topic_store.delete_association(map_identifier, association_identifier)
            topic_store.set_association(map_identifier, association)

            flash("Member successfully deleted.", "warning")
        else:
            flash("Member was not deleted.", "warning")
        return redirect(
            url_for(
                "association.view",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
                association_identifier=association_identifier,
            )
        )

    return render_template(
        "association/delete_member.html", topic_map=topic_map, topic=topic, association=association, member=member,
    )


@bp.route(
    "/associations/add-reference/<map_identifier>/<topic_identifier>/<association_identifier>/<member_identifier>",
    methods=("GET", "POST"),
)
@login_required
def add_reference(map_identifier, topic_identifier, association_identifier, member_identifier):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    association = topic_store.get_association(map_identifier, association_identifier)
    if association is None:
        abort(404)

    member = association.get_member(member_identifier)

    error = 0

    if request.method == "POST":
        form_topic_reference = request.form["topic-reference"].strip()

        # Validate form inputs
        if not form_topic_reference:
            error = error | 1
        if not topic_store.topic_exists(topic_map.identifier, form_topic_reference):
            error = error | 2

        if error != 0:
            flash(
                "An error occurred when submitting the form. Please review the warnings and fix accordingly.",
                "warning",
            )
        else:
            member.add_topic_ref(form_topic_reference)
            topic_store.delete_association(map_identifier, association_identifier)
            topic_store.set_association(map_identifier, association)

            flash("Topic reference successfully added.", "success")
            return redirect(
                url_for(
                    "association.view_member",
                    map_identifier=topic_map.identifier,
                    topic_identifier=topic.identifier,
                    association_identifier=association_identifier,
                    member_identifier=member_identifier,
                )
            )

        return render_template(
            "association/add_reference.html",
            error=error,
            topic_map=topic_map,
            topic=topic,
            association=association,
            member=member,
            topic_reference=form_topic_reference,
        )

    return render_template(
        "association/add_reference.html",
        error=error,
        topic_map=topic_map,
        topic=topic,
        association=association,
        member=member,
    )


@bp.route(
    "/associations/delete-reference/<map_identifier>/<topic_identifier>/<association_identifier>/<member_identifier>/<reference_identifier>",
    methods=("GET", "POST"),
)
@login_required
def delete_reference(
    map_identifier, topic_identifier, association_identifier, member_identifier, reference_identifier,
):
    topic_store = get_topic_store()

    topic_map = topic_store.get_topic_map(map_identifier, current_user.id)
    if topic_map is None:
        abort(404)
    # If the map doesn't belong to the user and they don't have the right
    # collaboration mode on the map, then abort
    if not topic_map.owner and topic_map.collaboration_mode is not CollaborationMode.EDIT:
        abort(403)

    topic = topic_store.get_topic(
        map_identifier, topic_identifier, resolve_attributes=RetrievalMode.RESOLVE_ATTRIBUTES,
    )
    if topic is None:
        abort(404)

    association = topic_store.get_association(map_identifier, association_identifier)
    if association is None:
        abort(404)

    member = association.get_member(member_identifier)

    form_topic_reference = reference_identifier

    if request.method == "POST":
        if len(member.topic_refs) > 1:
            member.remove_topic_ref(form_topic_reference)
            topic_store.delete_association(map_identifier, association_identifier)
            topic_store.set_association(map_identifier, association)

            flash("Topic reference successfully deleted.", "warning")
        else:
            flash("Topic reference was not deleted.", "warning")
        return redirect(
            url_for(
                "association.view_member",
                map_identifier=topic_map.identifier,
                topic_identifier=topic.identifier,
                association_identifier=association_identifier,
                member_identifier=member_identifier,
            )
        )

    return render_template(
        "association/delete_reference.html",
        topic_map=topic_map,
        topic=topic,
        association=association,
        member=member,
        topic_reference=form_topic_reference,
    )
