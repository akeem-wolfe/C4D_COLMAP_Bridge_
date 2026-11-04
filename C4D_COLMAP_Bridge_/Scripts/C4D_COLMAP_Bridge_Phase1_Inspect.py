# C4D to COLMAP Bridge — Phase 1 scene inspection
# Target: Cinema 4D R26 / macOS / Apple Silicon
#
# Run from Cinema 4D's Script Manager.
# READ-ONLY: this script does not move objects, render, or modify the scene.
# It writes a JSON camera report next to the open .c4d file.

import c4d
import json
import os
import traceback
from datetime import datetime


def vector_to_list(v):
    return [float(v.x), float(v.y), float(v.z)]


def matrix_to_dict(m):
    return {
        "position": vector_to_list(m.off),
        "axis_x": vector_to_list(m.v1),
        "axis_y": vector_to_list(m.v2),
        "axis_z": vector_to_list(m.v3)
    }


def walk_objects(parent):
    # The document lists root objects with GetFirstObject.
    # Scene objects list their children with GetDown.
    if isinstance(parent, c4d.documents.BaseDocument):
        obj = parent.GetFirstObject()
    else:
        obj = parent.GetDown()
    while obj:
        yield obj
        for child in walk_objects(obj):
            yield child
        obj = obj.GetNext()


def safe_parameter(obj, parameter_id):
    try:
        value = obj[parameter_id]
        if isinstance(value, c4d.Vector):
            return vector_to_list(value)
        if isinstance(value, (int, float, bool, str)):
            return value
        if value is None:
            return None
        return str(value)
    except Exception:
        return None


def main():
    doc = c4d.documents.GetActiveDocument()
    if doc is None:
        raise RuntimeError("No active Cinema 4D document.")

    render_data = doc.GetActiveRenderData()
    render_settings = {
        "width_px": int(render_data[c4d.RDATA_XRES]) if render_data else None,
        "height_px": int(render_data[c4d.RDATA_YRES]) if render_data else None,
        "pixel_aspect": safe_parameter(render_data, c4d.RDATA_PIXELASPECT) if render_data else None
    }

    cameras = []
    for obj in walk_objects(doc):
        if obj.CheckType(c4d.Ocamera):
            cameras.append({
                "name": obj.GetName(),
                "type_id": int(obj.GetType()),
                "world_matrix": matrix_to_dict(obj.GetMg()),
                "projection": safe_parameter(obj, c4d.CAMERA_PROJECTION),
                "focal_length_mm": safe_parameter(obj, c4d.CAMERA_FOCUS),
                "sensor_width_mm": safe_parameter(obj, c4d.CAMERAOBJECT_APERTURE),
                "horizontal_fov_raw": safe_parameter(obj, c4d.CAMERAOBJECT_FOV),
                "vertical_fov_raw": safe_parameter(obj, c4d.CAMERAOBJECT_FOV_VERTICAL),
                "film_offset_x": safe_parameter(obj, c4d.CAMERAOBJECT_FILM_OFFSET_X),
                "film_offset_y": safe_parameter(obj, c4d.CAMERAOBJECT_FILM_OFFSET_Y)
            })

    base_draw = doc.GetActiveBaseDraw()
    active_camera = base_draw.GetSceneCamera(doc) if base_draw is not None else None
    report = {
        "tool": "C4D to COLMAP Bridge — Phase 1 scene inspection",
        "plugin_id_reserved": 1073098,
        "created_utc": datetime.utcnow().isoformat() + "Z",
        "cinema4d_version": c4d.GetC4DVersion(),
        "document_name": doc.GetDocumentName(),
        "document_units": "Cinema 4D scene units; verify project scale",
        "active_camera": active_camera.GetName() if active_camera else None,
        "active_render_settings": render_settings,
        "camera_count": len(cameras),
        "cameras": cameras,
        "notes": [
            "Read-only report; no scene objects were changed.",
            "Camera world matrices are recorded as Cinema 4D exposes them.",
            "COLMAP coordinate conversion and intrinsic calibration are not applied in this diagnostic stage.",
            "Octane-specific render settings are not modified or assumed."
        ]
    }

    document_dir = doc.GetDocumentPath()
    if not document_dir:
        raise RuntimeError(
            "Save the Cinema 4D document first. The report is written next to the .c4d file."
        )
    output_path = os.path.join(document_dir, "C4D_COLMAP_Bridge_camera_report.json")

    with open(output_path, "w") as output_file:
        json.dump(report, output_file, indent=2, sort_keys=True)

    print("")
    print("C4D to COLMAP Bridge — Phase 1 inspection complete")
    print("Cameras found: {0}".format(len(cameras)))
    print("Render resolution: {0} x {1}".format(
        render_settings["width_px"], render_settings["height_px"]))
    print("Report saved to:")
    print(output_path)
    print("No scene objects were modified.")

    c4d.gui.MessageDialog(
        "Camera inspection complete.\n\n"
        "Cameras found: {0}\n"
        "Report saved to:\n{1}".format(len(cameras), output_path)
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(traceback.format_exc())
        c4d.gui.MessageDialog(
            "C4D to COLMAP Bridge inspection failed.\n\n"
            "See the Script Manager console for details."
        )
