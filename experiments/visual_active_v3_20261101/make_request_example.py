"""Create an explicitly synthetic request log. No inference, movement or training."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'praxis/src'))
from active_view.capture_requests import CameraPose,CaptureRequest,RequestJournal


def main():
    out=Path(__file__).resolve().parent/'example';out.mkdir(exist_ok=False)
    journal=RequestJournal(out/'capture_requests.jsonl')
    journal.decision(decision_id='example-decision-no-request',episode_id='example-only',scene_revision='static-1',
                     source_observation_ids=['example-initial-rgb'],needs_reobserve=False,request_image=False,
                     reason='Synthetic example: current evidence sufficient; no image requested.')
    request=CaptureRequest.new(episode_id='example-only',scene_revision='static-1',
                               source_observation_ids=('example-initial-rgb',),
                               desired_camera_pose=CameraPose((.35,-.10,.55),(0.,1.,0.,0.)),
                               reason='Synthetic example: request a less occluded view.',
                               target_scope='objects',target_track_ids=('predicted-track-example',),
                               model_revision='design-only-not-trained',calibration_id='example-calibration-not-for-execution',example_only=True)
    journal.create(request)
    journal.decision(decision_id='example-decision-request',episode_id=request.episode_id,scene_revision=request.scene_revision,
                     source_observation_ids=request.source_observation_ids,needs_reobserve=True,request_image=True,
                     reason=request.reason,request_id=request.request_id)
    journal.transition(request.request_id,'blocked',scene_revision='static-1',
                       reason='Example only: no validated trajectory supplied. No movement or capture executed.')
    (out/'README.md').write_text('Synthetic logging example only. Desired pose is saved even though the request is blocked. No model, capture, movement or training was executed.\n',encoding='utf-8')
    print(json.dumps(dict(example_only=True,training_started=False,request_id=request.request_id,
                         final_state=journal.state(request.request_id),events=len(journal.records()))))


if __name__=='__main__':main()
