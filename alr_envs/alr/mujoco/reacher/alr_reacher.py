import os

import numpy as np
from gym import utils
from gym.envs.mujoco import MujocoEnv

import alr_envs.utils.utils as alr_utils


class ALRReacherEnv(MujocoEnv, utils.EzPickle):
    def __init__(self, steps_before_reward: int = 200, n_links: int = 5, ctrl_cost_weight: int = 1,
                 balance: bool = False):
        utils.EzPickle.__init__(**locals())

        self._steps = 0
        self.steps_before_reward = steps_before_reward
        self.n_links = n_links

        self.balance = balance
        self.balance_weight = 1.0
        self.ctrl_cost_weight = ctrl_cost_weight

        self.reward_weight = 1
        if steps_before_reward == 200:
            self.reward_weight = 200
        elif steps_before_reward == 50:
            self.reward_weight = 50

        if n_links == 5:
            file_name = 'reacher_5links.xml'
        elif n_links == 7:
            file_name = 'reacher_7links.xml'
        else:
            raise ValueError(f"Invalid number of links {n_links}, only 5 or 7 allowed.")

        MujocoEnv.__init__(self, os.path.join(os.path.dirname(__file__), "assets", file_name), 2)

    def step(self, a):
        self._steps += 1

        reward_dist = 0.0
        angular_vel = 0.0
        reward_balance = 0.0
        is_delayed = self.steps_before_reward > 0
        reward_ctrl = - np.square(a).sum() * self.ctrl_cost_weight
        if self._steps >= self.steps_before_reward:
            vec = self.get_body_com("fingertip") - self.get_body_com("target")
            reward_dist -= self.reward_weight * np.linalg.norm(vec)
            if is_delayed:
                # avoid giving this penalty for normal step based case
                # angular_vel -= 10 * np.linalg.norm(self.sim.data.qvel.flat[:self.n_links])
                angular_vel -= 10 * np.square(self.sim.data.qvel.flat[:self.n_links]).sum()
        # if is_delayed:
        #     # Higher control penalty for sparse reward per timestep
        #     reward_ctrl *= 10

        if self.balance:
            reward_balance -= self.balance_weight * np.abs(
                alr_utils.angle_normalize(np.sum(self.sim.data.qpos.flat[:self.n_links]), type="rad"))

        reward = reward_dist + reward_ctrl + angular_vel + reward_balance
        self.do_simulation(a, self.frame_skip)
        ob = self._get_obs()
        done = False
        return ob, reward, done, dict(reward_dist=reward_dist, reward_ctrl=reward_ctrl,
                                      velocity=angular_vel, reward_balance=reward_balance,
                                      end_effector=self.get_body_com("fingertip").copy(),
                                      goal=self.goal if hasattr(self, "goal") else None)

    def viewer_setup(self):
        self.viewer.cam.trackbodyid = 0

    # def reset_model(self):
    #     qpos = self.init_qpos
    #     if not hasattr(self, "goal"):
    #         self.goal = np.array([-0.25, 0.25])
    #         # self.goal = self.init_qpos.copy()[:2] + 0.05
    #     qpos[-2:] = self.goal
    #     qvel = self.init_qvel
    #     qvel[-2:] = 0
    #     self.set_state(qpos, qvel)
    #     self._steps = 0
    #
    #     return self._get_obs()

    def reset_model(self):
        qpos = self.init_qpos.copy()
        while True:
            # full space
            # self.goal = self.np_random.uniform(low=-self.n_links / 10, high=self.n_links / 10, size=2)
            # I Quadrant
            # self.goal = self.np_random.uniform(low=0, high=self.n_links / 10, size=2)
            # II Quadrant
            # self.goal = np.random.uniform(low=[-self.n_links / 10, 0], high=[0, self.n_links / 10], size=2)
            # II + III Quadrant
            # self.goal = np.random.uniform(low=-self.n_links / 10, high=[0, self.n_links / 10], size=2)
            # I + II Quadrant
            self.goal = np.random.uniform(low=[-self.n_links / 10, 0], high=self.n_links, size=2)
            if np.linalg.norm(self.goal) < self.n_links / 10:
                break
        qpos[-2:] = self.goal
        qvel = self.init_qvel.copy()
        qvel[-2:] = 0
        self.set_state(qpos, qvel)
        self._steps = 0

        return self._get_obs()

    # def reset_model(self):
    #     qpos = self.np_random.uniform(low=-0.1, high=0.1, size=self.model.nq) + self.init_qpos
    #     while True:
    #         self.goal = self.np_random.uniform(low=-self.n_links / 10, high=self.n_links / 10, size=2)
    #         if np.linalg.norm(self.goal) < self.n_links / 10:
    #             break
    #     qpos[-2:] = self.goal
    #     qvel = self.init_qvel + self.np_random.uniform(low=-.005, high=.005, size=self.model.nv)
    #     qvel[-2:] = 0
    #     self.set_state(qpos, qvel)
    #     self._steps = 0
    #
    #     return self._get_obs()

    def _get_obs(self):
        theta = self.sim.data.qpos.flat[:self.n_links]
        target = self.get_body_com("target")
        return np.concatenate([
            np.cos(theta),
            np.sin(theta),
            target[:2],  # x-y of goal position
            self.sim.data.qvel.flat[:self.n_links],  # angular velocity
            self.get_body_com("fingertip") - target,  # goal distance
            [self._steps],
        ])


if __name__ == '__main__':
    nl = 5
    render_mode = "human"  # "human" or "partial" or "final"
    env = ALRReacherEnv(n_links=nl)
    obs = env.reset()

    for i in range(2000):
        # objective.load_result("/tmp/cma")
        # test with random actions
        ac = env.action_space.sample()
        obs, rew, d, info = env.step(ac)
        if i % 10 == 0:
            env.render(mode=render_mode)
        if d:
            env.reset()

    env.close()